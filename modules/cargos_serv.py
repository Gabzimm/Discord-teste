import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle
import asyncio
from datetime import datetime
from typing import Dict, List, Optional

# ========== CONFIGURAÇÃO ==========
class CargosServidor:
    """Classe para gerenciar os cargos do servidor"""
    
    def __init__(self):
        self.cache_cargos: Dict[int, List[discord.Role]] = {}
        self.cache_timestamp: Dict[int, datetime] = {}
    
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
        
        if guild.id not in self.cache_cargos:
            return self.atualizar_cache(guild)
        
        if guild.id in self.cache_timestamp:
            tempo_cache = (datetime.now() - self.cache_timestamp[guild.id]).total_seconds()
            if tempo_cache > 300:  # 5 minutos
                return self.atualizar_cache(guild)
        
        return self.cache_cargos[guild.id]

# ========== VIEW DO PAINEL DE CARGOS ==========
class PaginarCargosView(ui.View):
    """View com botões para paginar os cargos"""
    
    def __init__(self, cargos: List[discord.Role], items_por_pagina: int = 15):
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
        """Retorna embed da página atual - APENAS @ E POSIÇÃO"""
        
        inicio = self.pagina_atual * self.items_por_pagina
        fim = inicio + self.items_por_pagina
        cargos_pagina = self.cargos[inicio:fim]
        
        embed = discord.Embed(
            title="📋 Cargos do Servidor",
            description=f"Total de **{len(self.cargos)}** cargos encontrados",
            color=discord.Color.blue()
        )
        
        # Lista de cargos com posição e menção
        lista_cargos = []
        for i, cargo in enumerate(cargos_pagina, inicio + 1):
            lista_cargos.append(f"`{i:02d}.` {cargo.mention} • Posição `{cargo.position}`")
        
        embed.add_field(
            name="📌 Cargos",
            value="\n".join(lista_cargos) if lista_cargos else "Nenhum cargo",
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
            cog.gerenciador.atualizar_cache(interaction.guild)
            self.cargos = cog.gerenciador.get_cargos(interaction.guild)
            self.total_paginas = (len(self.cargos) + self.items_por_pagina - 1) // self.items_por_pagina
            self.pagina_atual = 0
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_pagina_embed(), view=self)
        else:
            await interaction.response.send_message("❌ Erro ao atualizar!", ephemeral=True)

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
    
    # ===== SLASH COMMANDS =====
    
    @app_commands.command(name="cargos", description="📋 Mostra todos os cargos do servidor")
    async def cargos_lista(self, interaction: discord.Interaction):
        """Comando /cargos - Lista todos os cargos do servidor com @"""
        
        cargos = self.gerenciador.get_cargos(interaction.guild)
        
        if not cargos:
            await interaction.response.send_message("❌ Nenhum cargo encontrado no servidor!", ephemeral=True)
            return
        
        # Criar view com paginação
        view = PaginarCargosView(cargos)
        
        await interaction.response.send_message(embed=view.get_pagina_embed(), view=view)

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(CargosServidorCog(bot))
    print("✅ Sistema de Cargos do Servidor configurado!")
