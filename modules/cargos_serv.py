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
    
    def atualizar_cache(self, guild: discord.Guild):
        """Atualiza o cache de cargos do servidor"""
        cargos = [role for role in guild.roles if role.name != "@everyone"]
        cargos.sort(key=lambda r: r.position, reverse=True)
        self.cache_cargos[guild.id] = cargos
        self.cache_timestamp[guild.id] = datetime.now()
        return cargos
    
    def get_cargos(self, guild: discord.Guild) -> List[discord.Role]:
        """Retorna os cargos do servidor"""
        if guild.id not in self.cache_cargos:
            return self.atualizar_cache(guild)
        
        if guild.id in self.cache_timestamp:
            tempo_cache = (datetime.now() - self.cache_timestamp[guild.id]).total_seconds()
            if tempo_cache > 300:
                return self.atualizar_cache(guild)
        
        return self.cache_cargos[guild.id]

# ========== VIEW DO PAINEL DE CARGOS ==========
class PaginarCargosView(ui.View):
    """View com botões para paginar os cargos - ATUALIZAÇÃO PERMANENTE"""
    
    def __init__(self, cargos: List[discord.Role], guild: discord.Guild, cog, items_por_pagina: int = 15):
        super().__init__(timeout=None)  # timeout=None = nunca expira
        self.cargos = cargos
        self.guild = guild
        self.cog = cog
        self.items_por_pagina = items_por_pagina
        self.pagina_atual = 0
        self.total_paginas = (len(cargos) + items_por_pagina - 1) // items_por_pagina if cargos else 1
        self.mensagem = None
        self.atualizando = True  # Flag para manter a atualização
    
        self.update_buttons()
        
        # Iniciar a tarefa de atualização automática (NUNCA PARA)
        self.atualizar_automatico.start()
    
    def update_buttons(self):
        """Atualiza estado dos botões"""
        if len(self.children) >= 2:
            self.children[0].disabled = self.pagina_atual == 0
            self.children[1].disabled = self.pagina_atual >= self.total_paginas - 1
    
    def get_posicao_hierarquica(self, cargo: discord.Role) -> int:
        """Calcula a posição real na hierarquia"""
        cargos_filtrados = [c for c in self.guild.roles if c.name != "@everyone"]
        cargos_filtrados.sort(key=lambda r: r.position, reverse=True)
        try:
            return cargos_filtrados.index(cargo) + 1
        except ValueError:
            return 0
    
    def get_pagina_embed(self) -> discord.Embed:
        """Retorna embed da página atual"""
        
        if not self.cargos:
            embed = discord.Embed(
                title="📋 Cargos do Servidor",
                description="Nenhum cargo encontrado!",
                color=discord.Color.red()
            )
            return embed
        
        inicio = self.pagina_atual * self.items_por_pagina
        fim = inicio + self.items_por_pagina
        cargos_pagina = self.cargos[inicio:fim]
        
        embed = discord.Embed(
            title="📋 Cargos do Servidor",
            description=f"Total de **{len(self.cargos)}** cargos encontrados",
            color=discord.Color.blue()
        )
        
        lista_cargos = []
        for i, cargo in enumerate(cargos_pagina, inicio + 1):
            posicao_hierarquica = self.get_posicao_hierarquica(cargo)
            lista_cargos.append(f"`{i:02d}.` {cargo.mention} • Posição `#{posicao_hierarquica}` na hierarquia")
        
        embed.add_field(
            name="📌 Cargos (Ordem Hierárquica - #1 é o mais alto)",
            value="\n".join(lista_cargos) if lista_cargos else "Nenhum cargo",
            inline=False
        )
        
        agora = datetime.now().strftime("%H:%M:%S")
        embed.set_footer(text=f"Página {self.pagina_atual + 1}/{self.total_paginas} • Atualizado automático • {agora}")
        
        return embed
    
    @tasks.loop(seconds=1.0)  # Atualiza a cada 1 segundo (mais estável)
    async def atualizar_automatico(self):
        """Atualiza automaticamente a lista de cargos - NUNCA PARA"""
        try:
            if not self.atualizando:
                return
            
            if not self.cog or not self.guild:
                return
            
            # Buscar cargos atualizados
            novos_cargos = self.cog.gerenciador.get_cargos(self.guild)
            
            # Verificar se houve mudança
            if len(novos_cargos) != len(self.cargos):
                self.cargos = novos_cargos
                self.total_paginas = (len(self.cargos) + self.items_por_pagina - 1) // self.items_por_pagina if self.cargos else 1
                
                # Ajustar página atual se necessário
                if self.pagina_atual >= self.total_paginas and self.total_paginas > 0:
                    self.pagina_atual = self.total_paginas - 1
                elif self.total_paginas == 0:
                    self.pagina_atual = 0
                
                self.update_buttons()
                
                # Atualizar mensagem
                if self.mensagem:
                    try:
                        await self.mensagem.edit(embed=self.get_pagina_embed(), view=self)
                    except:
                        pass
            else:
                # Mesmo sem mudança, atualizar o timestamp no footer
                if self.mensagem:
                    try:
                        await self.mensagem.edit(embed=self.get_pagina_embed(), view=self)
                    except:
                        pass
                    
        except Exception as e:
            print(f"⚠️ Erro na atualização automática: {e}")
    
    @atualizar_automatico.before_loop
    async def before_atualizar(self):
        """Aguardar o bot estar pronto antes de começar"""
        await self.cog.bot.wait_until_ready()
        print("✅ Atualização automática de cargos iniciada!")
    
    async def on_error(self, error, *args, **kwargs):
        """Trata erros da task"""
        print(f"❌ Erro na task de atualização: {error}")
    
    def stop_atualizacao(self):
        """Para a atualização automática"""
        self.atualizando = False
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
        print("✅ Cog CargosServidorCog carregado!")
    
    def cog_unload(self):
        """Quando o cog é descarregado, parar todas as atualizações"""
        for view in self.views_ativas.values():
            view.stop_atualizacao()
        print("🛑 Todas as atualizações de cargos foram paradas")
    
    # ===== EVENTOS =====
    
    @commands.Cog.listener()
    async def on_guild_role_create(self, role: discord.Role):
        """Quando um cargo é criado - atualiza cache"""
        self.gerenciador.atualizar_cache(role.guild)
        print(f"📌 Cargo criado: {role.name} em {role.guild.name}")
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Quando um cargo é deletado - atualiza cache"""
        self.gerenciador.atualizar_cache(role.guild)
        print(f"🗑️ Cargo deletado: {role.name} em {role.guild.name}")
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Quando um cargo é atualizado - atualiza cache"""
        if before.name != after.name or before.color != after.color or before.position != after.position:
            self.gerenciador.atualizar_cache(after.guild)
            print(f"✏️ Cargo atualizado: {after.name} em {after.guild.name}")
    
    # ===== COMANDOS COM PREFIXO ! =====
    
    @commands.command(name="cargos")
    async def cargos_comando(self, ctx):
        """!cargos - Mostra todos os cargos do servidor (atualiza automático)"""
        
        cargos = self.gerenciador.get_cargos(ctx.guild)
        
        if not cargos:
            await ctx.send("❌ Nenhum cargo encontrado no servidor!")
            return
        
        # Parar view antiga neste canal se existir
        if ctx.channel.id in self.views_ativas:
            self.views_ativas[ctx.channel.id].stop_atualizacao()
            del self.views_ativas[ctx.channel.id]
        
        # Criar nova view com atualização automática PERMANENTE
        view = PaginarCargosView(cargos, ctx.guild, self)
        
        # Enviar mensagem
        mensagem = await ctx.send(embed=view.get_pagina_embed(), view=view)
        view.mensagem = mensagem
        
        # Guardar view ativa
        self.views_ativas[ctx.channel.id] = view
        
        print(f"✅ Painel de cargos aberto em #{ctx.channel.name} em {ctx.guild.name}")
    
    @commands.command(name="cargos_parar")
    async def cargos_parar_comando(self, ctx):
        """!cargos_parar - Para a atualização automática dos cargos"""
        
        if ctx.channel.id in self.views_ativas:
            self.views_ativas[ctx.channel.id].stop_atualizacao()
            del self.views_ativas[ctx.channel.id]
            await ctx.send("✅ Atualização automática parada!")
        else:
            await ctx.send("❌ Nenhuma atualização ativa neste canal!")
    
    @commands.command(name="cargos_atualizar")
    async def cargos_atualizar_comando(self, ctx):
        """!cargos_atualizar - Força atualização manual dos cargos"""
        
        cargos = self.gerenciador.atualizar_cache(ctx.guild)
        
        embed = discord.Embed(
            title="🔄 Cache Atualizado",
            description=f"**{len(cargos)}** cargos encontrados no servidor",
            color=discord.Color.green()
        )
        
        await ctx.send(embed=embed)

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(CargosServidorCog(bot))
    print("✅ Sistema de Cargos do Servidor configurado com !cargos!")
