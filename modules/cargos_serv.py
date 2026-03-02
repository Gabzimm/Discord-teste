import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle
import asyncio
from datetime import datetime
from typing import Dict, List, Optional
import json
import os

# ========== CONFIGURAÇÃO ==========
class CargosServidor:
    """Classe para gerenciar os cargos do servidor"""
    
    def __init__(self):
        self.cache_cargos: Dict[int, List[discord.Role]] = {}  # guild_id: [roles]
        self.cache_timestamp: Dict[int, datetime] = {}  # guild_id: timestamp
    
    def atualizar_cache(self, guild: discord.Guild):
        """Atualiza o cache de cargos do servidor"""
        # Pegar todos os cargos (exceto @everyone)
        cargos = [role for role in guild.roles if role.name != "@everyone"]
        
        # Ordenar por posição (do maior para o menor)
        cargos.sort(key=lambda r: r.position, reverse=True)
        
        self.cache_cargos[guild.id] = cargos
        self.cache_timestamp[guild.id] = datetime.now()
        
        return cargos
    
    def get_cargos(self, guild: discord.Guild) -> List[discord.Role]:
        """Retorna os cargos do servidor (do cache ou atualiza)"""
        
        # Se não tiver cache ou cache antigo (> 5 minutos), atualiza
        if guild.id not in self.cache_cargos:
            return self.atualizar_cache(guild)
        
        # Verificar se cache está atualizado (5 minutos)
        if guild.id in self.cache_timestamp:
            tempo_cache = (datetime.now() - self.cache_timestamp[guild.id]).total_seconds()
            if tempo_cache > 300:  # 5 minutos
                return self.atualizar_cache(guild)
        
        return self.cache_cargos[guild.id]
    
    def get_cargo_por_nome(self, guild: discord.Guild, nome: str) -> Optional[discord.Role]:
        """Busca cargo por nome (case insensitive)"""
        cargos = self.get_cargos(guild)
        nome_lower = nome.lower()
        
        for cargo in cargos:
            if cargo.name.lower() == nome_lower:
                return cargo
        return None
    
    def get_cargos_por_cor(self, guild: discord.Guild, cor: discord.Color) -> List[discord.Role]:
        """Busca cargos por cor"""
        cargos = self.get_cargos(guild)
        return [cargo for cargo in cargos if cargo.color == cor]
    
    def get_cargos_por_permissao(self, guild: discord.Guild, permissao: str) -> List[discord.Role]:
        """Busca cargos que têm uma permissão específica"""
        cargos = self.get_cargos(guild)
        return [cargo for cargo in cargos if getattr(cargo.permissions, permissao, False)]

# ========== VIEW DO PAINEL DE CARGOS ==========
class PaginarCargosView(ui.View):
    """View com botões para paginar os cargos"""
    
    def __init__(self, cargos: List[discord.Role], items_por_pagina: int = 10):
        super().__init__(timeout=60)
        self.cargos = cargos
        self.items_por_pagina = items_por_pagina
        self.pagina_atual = 0
        self.total_paginas = (len(cargos) + items_por_pagina - 1) // items_por_pagina
        
        self.update_buttons()
    
    def update_buttons(self):
        """Atualiza estado dos botões"""
        self.children[0].disabled = self.pagina_atual == 0
        self.children[1].disabled = self.pagina_atual >= self.total_paginas - 1
    
    def get_pagina_embed(self) -> discord.Embed:
        """Retorna embed da página atual"""
        
        inicio = self.pagina_atual * self.items_por_pagina
        fim = inicio + self.items_por_pagina
        cargos_pagina = self.cargos[inicio:fim]
        
        embed = discord.Embed(
            title="📋 Cargos do Servidor",
            description=f"Total de **{len(self.cargos)}** cargos encontrados",
            color=discord.Color.blue()
        )
        
        for i, cargo in enumerate(cargos_pagina, inicio + 1):
            # Informações do cargo
            info = []
            
            # Cor (se não for padrão)
            if cargo.color.value != 0:
                info.append(f"🎨 Cor: `#{cargo.color.value:06x}`")
            
            # Menção
            info.append(f"📌 Menção: {cargo.mention}")
            
            # Posição
            info.append(f"📊 Posição: `{cargo.position}`")
            
            # Membros
            membros = len([m for m in cargo.members if not m.bot])
            bots = len([m for m in cargo.members if m.bot])
            info.append(f"👥 Membros: `{membros}` humanos, `{bots}` bots")
            
            # Data de criação
            info.append(f"📅 Criado: {cargo.created_at.strftime('%d/%m/%Y')}")
            
            embed.add_field(
                name=f"{i}. {cargo.name}",
                value="\n".join(info),
                inline=False
            )
        
        embed.set_footer(text=f"Página {self.pagina_atual + 1}/{self.total_paginas}")
        return embed
    
    @ui.button(label="◀️ Anterior", style=ButtonStyle.blurple)
    async def anterior(self, interaction: discord.Interaction, button: ui.Button):
        self.pagina_atual -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_pagina_embed(), view=self)
    
    @ui.button(label="Próxima ▶️", style=ButtonStyle.blurple)
    async def proxima(self, interaction: discord.Interaction, button: ui.Button):
        self.pagina_atual += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_pagina_embed(), view=self)
    
    @ui.button(label="🔄 Atualizar", style=ButtonStyle.green)
    async def atualizar(self, interaction: discord.Interaction, button: ui.Button):
        """Força atualização da lista"""
        cog = interaction.client.get_cog("CargosServidorCog")
        if cog:
            # Forçar atualização do cache
            cog.gerenciador.atualizar_cache(interaction.guild)
            self.cargos = cog.gerenciador.get_cargos(interaction.guild)
            self.total_paginas = (len(self.cargos) + self.items_por_pagina - 1) // self.items_por_pagina
            self.pagina_atual = 0
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_pagina_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Erro ao atualizar!", ephemeral=True)

class DetalheCargoView(ui.View):
    """View com detalhes de um cargo específico"""
    
    def __init__(self, cargo: discord.Role):
        super().__init__(timeout=60)
        self.cargo = cargo
    
    def get_embed(self) -> discord.Embed:
        """Retorna embed com detalhes do cargo"""
        
        embed = discord.Embed(
            title=f"📌 Detalhes do Cargo: {self.cargo.name}",
            color=self.cargo.color if self.cargo.color.value != 0 else discord.Color.blue()
        )
        
        # Informações básicas
        embed.add_field(name="🆔 ID", value=f"`{self.cargo.id}`", inline=True)
        embed.add_field(name="📊 Posição", value=f"`{self.cargo.position}`", inline=True)
        embed.add_field(name="🎨 Cor", value=f"`#{self.cargo.color.value:06x}`" if self.cargo.color.value != 0 else "`Padrão`", inline=True)
        
        # Membros
        membros = [m for m in self.cargo.members if not m.bot]
        bots = [m for m in self.cargo.members if m.bot]
        
        embed.add_field(name="👥 Membros", value=f"`{len(membros)}` humanos", inline=True)
        embed.add_field(name="🤖 Bots", value=f"`{len(bots)}` bots", inline=True)
        embed.add_field(name="📅 Criado", value=self.cargo.created_at.strftime('%d/%m/%Y'), inline=True)
        
        # Menção
        embed.add_field(name="📌 Menção", value=self.cargo.mention, inline=False)
        
        # Permissões principais
        permissoes = []
        for perm, valor in self.cargo.permissions:
            if valor:
                nome_perm = perm.replace('_', ' ').title()
                permissoes.append(f"✅ {nome_perm}")
        
        if permissoes:
            embed.add_field(
                name="🔒 Permissões",
                value="\n".join(permissoes[:10]) + ("\n..." if len(permissoes) > 10 else ""),
                inline=False
            )
        
        return embed
    
    @ui.button(label="🔙 Voltar", style=ButtonStyle.gray)
    async def voltar(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.edit_message(view=None, content="👋 Comando finalizado!", embed=None)

# ========== MODAL PARA BUSCAR CARGO ==========
class BuscarCargoModal(ui.Modal, title="🔍 Buscar Cargo"):
    
    nome_cargo = ui.TextInput(
        label="Nome do cargo:",
        placeholder="Digite o nome do cargo...",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        cog = interaction.client.get_cog("CargosServidorCog")
        if not cog:
            await interaction.followup.send("❌ Erro ao buscar cargo!", ephemeral=True)
            return
        
        cargo = cog.gerenciador.get_cargo_por_nome(interaction.guild, self.nome_cargo.value)
        
        if not cargo:
            await interaction.followup.send(f"❌ Cargo `{self.nome_cargo.value}` não encontrado!", ephemeral=True)
            return
        
        view = DetalheCargoView(cargo)
        await interaction.followup.send(embed=view.get_embed(), view=view, ephemeral=True)

# ========== COG PRINCIPAL ==========
class CargosServidorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gerenciador = CargosServidor()
        print("✅ Sistema de Cargos do Servidor carregado!")
    
    # ===== EVENTOS =====
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Quando um cargo é criado"""
        self.gerenciador.atualizar_cache(role.guild)
        print(f"📌 Cargo criado em {role.guild.name}: {role.name}")
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Quando um cargo é deletado"""
        self.gerenciador.atualizar_cache(role.guild)
        print(f"🗑️ Cargo removido de {role.guild.name}: {role.name}")
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Quando um cargo é atualizado"""
        if before.name != after.name or before.color != after.color:
            self.gerenciador.atualizar_cache(after.guild)
            print(f"✏️ Cargo atualizado em {after.guild.name}: {after.name}")
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Quando membro ganha/perde cargo"""
        if before.roles != after.roles:
            # Pode atualizar cache se quiser, mas não é necessário
            pass
    
    # ===== SLASH COMMANDS =====
    
    @app_commands.command(name="cargos", description="📋 Mostra todos os cargos do servidor")
    async def cargos_lista(self, interaction: discord.Interaction):
        """Comando /cargos - Lista todos os cargos do servidor"""
        
        cargos = self.gerenciador.get_cargos(interaction.guild)
        
        if not cargos:
            await interaction.response.send_message("❌ Nenhum cargo encontrado no servidor!", ephemeral=True)
            return
        
        # Criar view com paginação
        view = PaginarCargosView(cargos)
        
        await interaction.response.send_message(embed=view.get_pagina_embed(), view=view)
    
    @app_commands.command(name="cargo", description="🔍 Mostra detalhes de um cargo específico")
    async def cargo_detalhe(self, interaction: discord.Interaction, cargo: discord.Role):
        """Comando /cargo - Mostra detalhes de um cargo"""
        
        view = DetalheCargoView(cargo)
        await interaction.response.send_message(embed=view.get_embed(), view=view)
    
    @app_commands.command(name="cargo_buscar", description="🔎 Busca um cargo pelo nome")
    async def cargo_buscar(self, interaction: discord.Interaction):
        """Comando /cargo_buscar - Abre modal para buscar cargo"""
        
        await interaction.response.send_modal(BuscarCargoModal())
    
    @app_commands.command(name="cargos_stats", description="📊 Estatísticas dos cargos do servidor")
    async def cargos_stats(self, interaction: discord.Interaction):
        """Comando /cargos_stats - Mostra estatísticas"""
        
        cargos = self.gerenciador.get_cargos(interaction.guild)
        
        # Estatísticas
        total_cargos = len(cargos)
        cargos_cores = len([c for c in cargos if c.color.value != 0])
        cargos_mencionaveis = len([c for c in cargos if c.mentionable])
        cargos_separados = len([c for c in cargos if c.hoist])
        
        # Cargos com mais membros
        cargos_por_membros = sorted(cargos, key=lambda c: len(c.members), reverse=True)[:5]
        
        embed = discord.Embed(
            title="📊 Estatísticas de Cargos",
            description=f"Servidor: **{interaction.guild.name}**",
            color=discord.Color.gold()
        )
        
        embed.add_field(name="📋 Total de Cargos", value=f"`{total_cargos}`", inline=True)
        embed.add_field(name="🎨 Com Cores", value=f"`{cargos_cores}`", inline=True)
        embed.add_field(name="📌 Mencionáveis", value=f"`{cargos_mencionaveis}`", inline=True)
        embed.add_field(name="🔝 Separados", value=f"`{cargos_separados}`", inline=True)
        
        # Top 5 cargos com mais membros
        top_cargos = []
        for cargo in cargos_por_membros:
            if cargo.name != "@everyone":
                membros = len([m for m in cargo.members if not m.bot])
                top_cargos.append(f"• **{cargo.name}**: `{membros}` membros")
        
        if top_cargos:
            embed.add_field(
                name="🏆 Top 5 Cargos (mais membros)",
                value="\n".join(top_cargos),
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="cargos_atualizar", description="🔄 Força atualização do cache de cargos")
    @app_commands.default_permissions(administrator=True)
    async def cargos_atualizar(self, interaction: discord.Interaction):
        """Comando /cargos_atualizar - Força atualização manual"""
        
        await interaction.response.defer(ephemeral=True)
        
        antes = len(self.gerenciador.get_cargos(interaction.guild))
        self.gerenciador.atualizar_cache(interaction.guild)
        depois = len(self.gerenciador.get_cargos(interaction.guild))
        
        await interaction.followup.send(
            f"✅ Cache atualizado! `{antes}` → `{depois}` cargos",
            ephemeral=True
        )

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(CargosServidorCog(bot))
    print("✅ Sistema de Cargos do Servidor configurado!")
