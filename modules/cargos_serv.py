import discord
from discord.ext import commands, tasks
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
        self.atualizacao_ativa = False
    
    def atualizar_cache(self, guild: discord.Guild):
        """Atualiza o cache de cargos do servidor"""
        # Pegar todos os cargos (exceto @everyone)
        cargos = [role for role in guild.roles if role.name != "@everyone"]
        
        # ORDENAR POR POSIÇÃO (DO MAIOR PARA O MENOR)
        # Quanto maior a posição, mais alto na hierarquia
        cargos.sort(key=lambda r: r.position, reverse=True)
        
        self.cache_cargos[guild.id] = cargos
        self.cache_timestamp[guild.id] = datetime.now()
        
        return cargos
    
    def get_cargos(self, guild: discord.Guild) -> List[discord.Role]:
        """Retorna os cargos do servidor (sempre atualizado)"""
        return self.atualizar_cache(guild)

# ========== VIEW DO PAINEL DE CARGOS ==========
class PaginarCargosView(ui.View):
    """View com botões para paginar os cargos"""
    
    def __init__(self, cargos: List[discord.Role], guild: discord.Guild, cog, items_por_pagina: int = 15):
        super().__init__(timeout=None)
        self.cargos = cargos
        self.guild = guild
        self.cog = cog
        self.items_por_pagina = items_por_pagina
        self.pagina_atual = 0
        self.total_paginas = (len(cargos) + items_por_pagina - 1) // items_por_pagina
        self.mensagem = None
        self.interaction = None
        
        self.update_buttons()
        
        # Iniciar tarefa de atualização automática
        self.atualizar_automatico.start()
    
    def update_buttons(self):
        """Atualiza estado dos botões"""
        if len(self.children) >= 2:
            self.children[0].disabled = self.pagina_atual == 0
            self.children[1].disabled = self.pagina_atual >= self.total_paginas - 1
    
    def get_posicao_hierarquica(self, cargo: discord.Role) -> int:
        """
        Calcula a posição real na hierarquia (ignorando @everyone)
        O cargo mais alto = posição 1
        """
        # Filtrar apenas cargos que não são @everyone
        cargos_filtrados = [c for c in self.guild.roles if c.name != "@everyone"]
        
        # Ordenar por posição (do maior para o menor)
        cargos_filtrados.sort(key=lambda r: r.position, reverse=True)
        
        # Encontrar a posição do cargo (1-based)
        try:
            return cargos_filtrados.index(cargo) + 1
        except ValueError:
            return 0
    
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
        
        # Lista de cargos com posição hierárquica REAL
        lista_cargos = []
        for i, cargo in enumerate(cargos_pagina, inicio + 1):
            # Posição real na hierarquia (1 = mais alto)
            posicao_hierarquica = self.get_posicao_hierarquica(cargo)
            
            # Posição raw do Discord (para referência)
            posicao_raw = cargo.position
            
            # Mostrar apenas a posição hierárquica (mais intuitiva)
            lista_cargos.append(f"`{i:02d}.` {cargo.mention} • Posição `#{posicao_hierarquica}` na hierarquia")
        
        embed.add_field(
            name="📌 Cargos (Ordem Hierárquica - #1 é o mais alto)",
            value="\n".join(lista_cargos) if lista_cargos else "Nenhum cargo",
            inline=False
        )
        
        # Informações de atualização
        agora = datetime.now().strftime("%H:%M:%S")
        embed.set_footer(text=f"Página {self.pagina_atual + 1}/{self.total_paginas} • Atualizado automático • {agora}")
        
        return embed
    
    @tasks.loop(seconds=0.5)
    async def atualizar_automatico(self):
        """Atualiza automaticamente a lista de cargos"""
        try:
            if not self.cog or not self.guild:
                return
            
            # Atualizar cache de cargos
            self.cargos = self.cog.gerenciador.get_cargos(self.guild)
            self.total_paginas = (len(self.cargos) + self.items_por_pagina - 1) // self.items_por_pagina
            
            # Ajustar página atual se necessário
            if self.pagina_atual >= self.total_paginas and self.total_paginas > 0:
                self.pagina_atual = self.total_paginas - 1
            elif self.total_paginas == 0:
                self.pagina_atual = 0
            
            self.update_buttons()
            
            # Atualizar mensagem se existir
            if self.mensagem:
                try:
                    await self.mensagem.edit(embed=self.get_pagina_embed(), view=self)
                except:
                    pass
                    
        except Exception as e:
            print(f"Erro na atualização automática: {e}")
    
    @atualizar_automatico.before_loop
    async def before_atualizar(self):
        """Aguardar o bot estar pronto"""
        await self.cog.bot.wait_until_ready()
    
    async def on_timeout(self):
        """Quando a view expirar"""
        self.atualizar_automatico.cancel()
    
    def stop_atualizacao(self):
        """Para a atualização automática"""
        self.atualizar_automatico.cancel()
    
    @ui.button(label="◀️ Anterior", style=ButtonStyle.blurple, custom_id="cargos_anterior")
    async def anterior(self, interaction: discord.Interaction, button: ui.Button):
        self.pagina_atual -= 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_pagina_embed(), view=self)
    
    @ui.button(label="Próxima ▶️", style=ButtonStyle.blurple, custom_id="cargos_proxima")
    async def proxima(self, interaction: discord.Interaction, button: ui.Button):
        self.pagina_atual += 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_pagina_embed(), view=self)

# ========== COG PRINCIPAL ==========
class CargosServidorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gerenciador = CargosServidor()
        self.views_ativas: Dict[int, PaginarCargosView] = {}
        print("✅ Sistema de Cargos do Servidor carregado!")
    
    def cog_unload(self):
        """Quando o cog é descarregado, parar todas as atualizações"""
        for view in self.views_ativas.values():
            view.stop_atualizacao()
    
    # ===== EVENTOS =====
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Quando um cargo é criado"""
        print(f"📌 Cargo criado em {role.guild.name}: {role.name}")
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Quando um cargo é deletado"""
        print(f"🗑️ Cargo removido de {role.guild.name}: {role.name}")
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Quando um cargo é atualizado"""
        if before.name != after.name or before.color != after.color or before.position != after.position:
            print(f"✏️ Cargo atualizado em {after.guild.name}: {after.name}")
    
    # ===== SLASH COMMANDS =====
    
    @app_commands.command(name="cargos", description="📋 Mostra todos os cargos do servidor (atualiza automático)")
    async def cargos_lista(self, interaction: discord.Interaction):
        """Comando /cargos - Lista todos os cargos do servidor"""
        
        await interaction.response.defer()
        
        cargos = self.gerenciador.get_cargos(interaction.guild)
        
        if not cargos:
            await interaction.followup.send("❌ Nenhum cargo encontrado no servidor!", ephemeral=True)
            return
        
        # Parar view antiga neste canal se existir
        if interaction.channel_id in self.views_ativas:
            self.views_ativas[interaction.channel_id].stop_atualizacao()
        
        # Criar nova view com atualização automática
        view = PaginarCargosView(cargos, interaction.guild, self)
        view.interaction = interaction
        
        # Enviar mensagem
        mensagem = await interaction.followup.send(embed=view.get_pagina_embed(), view=view, wait=True)
        view.mensagem = mensagem
        
        # Guardar view ativa
        self.views_ativas[interaction.channel_id] = view
    
    @app_commands.command(name="cargos_parar", description="⏹️ Para a atualização automática dos cargos")
    async def cargos_parar(self, interaction: discord.Interaction):
        """Comando para parar a atualização automática"""
        
        if interaction.channel_id in self.views_ativas:
            self.views_ativas[interaction.channel_id].stop_atualizacao()
            del self.views_ativas[interaction.channel_id]
            await interaction.response.send_message("✅ Atualização automática parada!", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nenhuma atualização ativa neste canal!", ephemeral=True)
    
    @app_commands.command(name="cargos_forcar", description="🔄 Força atualização manual dos cargos")
    async def cargos_forcar(self, interaction: discord.Interaction):
        """Comando para forçar atualização manual"""
        
        cargos = self.gerenciador.atualizar_cache(interaction.guild)
        
        # Calcular posições hierárquicas
        cargos_filtrados = [c for c in interaction.guild.roles if c.name != "@everyone"]
        cargos_filtrados.sort(key=lambda r: r.position, reverse=True)
        
        embed = discord.Embed(
            title="🔄 Cache Atualizado",
            description=f"**{len(cargos)}** cargos encontrados no servidor",
            color=discord.Color.green()
        )
        
        # Mostrar os 5 primeiros com posição correta
        if cargos_filtrados:
            exemplo = []
            for i, cargo in enumerate(cargos_filtrados[:5], 1):
                exemplo.append(f"`#{i}` {cargo.mention}")
            embed.add_field(name="📌 Top 5 Cargos", value="\n".join(exemplo), inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="cargos_debug", description="🔧 Mostra informações de debug dos cargos (admin)")
    @app_commands.default_permissions(administrator=True)
    async def cargos_debug(self, interaction: discord.Interaction):
        """Comando para debug - mostra posições raw"""
        
        # Todos os cargos (incluindo @everyone)
        todos_cargos = interaction.guild.roles
        todos_cargos.sort(key=lambda r: r.position, reverse=True)
        
        embed = discord.Embed(
            title="🔧 Debug de Cargos",
            description="Mostrando posições RAW do Discord",
            color=discord.Color.orange()
        )
        
        debug_info = []
        for cargo in todos_cargos[:10]:  # Mostrar apenas os 10 primeiros
            debug_info.append(f"`{cargo.name}` • Posição RAW: `{cargo.position}`")
        
        embed.add_field(name="📊 Posições RAW", value="\n".join(debug_info), inline=False)
        embed.set_footer(text="@everyone tem posição 0 • Quanto maior a posição, mais alto na hierarquia")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(CargosServidorCog(bot))
    print("✅ Sistema de Cargos do Servidor configurado com atualização automática!")
