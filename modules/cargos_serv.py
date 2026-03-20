import discord
from discord.ext import commands, tasks
from discord import ui, ButtonStyle
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
        """Atualiza o cache de cargos do servidor - ORDENADO POR POSIÇÃO"""
        # Pegar todos os cargos (exceto @everyone)
        cargos = [role for role in guild.roles if role.name != "@everyone"]
        
        # ORDENAR POR POSIÇÃO (do maior para o menor)
        # Isso garante que a ordem mostrada seja a ordem real da hierarquia
        cargos.sort(key=lambda r: r.position, reverse=True)
        
        self.cache_cargos[guild.id] = cargos
        self.cache_timestamp[guild.id] = datetime.now()
        
        print(f"🔄 Cache atualizado em {guild.name}: {len(cargos)} cargos ordenados")
        return cargos
    
    def get_cargos(self, guild: discord.Guild) -> List[discord.Role]:
        """Retorna os cargos do servidor em ordem hierárquica"""
        # SEMPRE atualizar para garantir ordem correta
        return self.atualizar_cache(guild)

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
        
        # Iniciar a tarefa de atualização automática
        self.atualizar_automatico.start()
    
    def update_buttons(self):
        """Atualiza estado dos botões"""
        if len(self.children) >= 2:
            self.children[0].disabled = self.pagina_atual == 0
            self.children[1].disabled = self.pagina_atual >= self.total_paginas - 1
    
    def get_posicao_hierarquica(self, cargo: discord.Role) -> int:
        """Calcula a posição real na hierarquia (1 = mais alto)"""
        # ORDENAR POR POSIÇÃO REAL
        cargos_filtrados = [c for c in self.guild.roles if c.name != "@everyone"]
        cargos_filtrados.sort(key=lambda r: r.position, reverse=True)
        
        try:
            # Posição na lista (começando de 1)
            return cargos_filtrados.index(cargo) + 1
        except ValueError:
            return 0
    
    def get_pagina_embed(self) -> discord.Embed:
        """Retorna embed da página atual - COM ORDEM CORRETA"""
        
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
        
        # Lista de cargos na ORDEM HIERÁRQUICA CORRETA
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
    
    @tasks.loop(seconds=1.0)  # Atualiza a cada 1 segundo
    async def atualizar_automatico(self):
        """Atualiza automaticamente a lista de cargos - REORDENA QUANDO MUDA"""
        try:
            if not self.atualizando:
                return
            
            if not self.cog or not self.guild:
                return
            
            # Buscar cargos atualizados (já vem ordenado corretamente)
            novos_cargos = self.cog.gerenciador.get_cargos(self.guild)
            
            # Verificar se a ORDEM mudou (comparar posições)
            ordem_mudou = False
            if len(novos_cargos) == len(self.cargos):
                for i, cargo in enumerate(novos_cargos):
                    if i < len(self.cargos):
                        if cargo.id != self.cargos[i].id:
                            ordem_mudou = True
                            break
            else:
                ordem_mudou = True
            
            # Se houve mudança na ordem ou quantidade
            if ordem_mudou:
                self.cargos = novos_cargos
                self.total_paginas = (len(self.cargos) + self.items_por_pagina - 1) // self.items_por_pagina if self.cargos else 1
                
                # Ajustar página atual se necessário
                if self.pagina_atual >= self.total_paginas and self.total_paginas > 0:
                    self.pagina_atual = self.total_paginas - 1
                elif self.total_paginas == 0:
                    self.pagina_atual = 0
                
                self.update_buttons()
                
                # Atualizar mensagem com nova ordem
                if self.mensagem:
                    try:
                        await self.mensagem.edit(embed=self.get_pagina_embed(), view=self)
                        print(f"🔄 Ordem dos cargos atualizada em {self.guild.name}")
                    except Exception as e:
                        print(f"⚠️ Erro ao atualizar mensagem: {e}")
            else:
                # Mesmo sem mudança na ordem, atualizar o timestamp
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
        """Quando um cargo é criado - ATUALIZA ORDEM"""
        self.gerenciador.atualizar_cache(role.guild)
        print(f"📌 Cargo CRIADO: {role.name} em {role.guild.name}")
        print(f"   Nova ordem será atualizada automaticamente")
    
    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role):
        """Quando um cargo é deletado - ATUALIZA ORDEM"""
        self.gerenciador.atualizar_cache(role.guild)
        print(f"🗑️ Cargo DELETADO: {role.name} em {role.guild.name}")
        print(f"   Nova ordem será atualizada automaticamente")
    
    @commands.Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role):
        """Quando um cargo é atualizado (nome, cor, POSIÇÃO)"""
        # Verificar se a POSIÇÃO mudou
        if before.position != after.position:
            self.gerenciador.atualizar_cache(after.guild)
            print(f"🔄 CARGO MOVIDO: {after.name} em {after.guild.name}")
            print(f"   Posição anterior: {before.position} → Nova posição: {after.position}")
            print(f"   A ordem será atualizada automaticamente")
        elif before.name != after.name:
            self.gerenciador.atualizar_cache(after.guild)
            print(f"✏️ Cargo RENOMEADO: {before.name} → {after.name} em {after.guild.name}")
    
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
        print(f"   Ordem atual: {len(cargos)} cargos na hierarquia")
    
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
        
        # Mostrar a ordem atual
        if cargos:
            top_cargos = []
            for i, cargo in enumerate(cargos[:5], 1):
                top_cargos.append(f"`#{i}` {cargo.mention}")
            embed.add_field(name="📌 Ordem Atual (Top 5)", value="\n".join(top_cargos), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="cargos_ordem")
    async def cargos_ordem_comando(self, ctx):
        """!cargos_ordem - Mostra a ordem atual dos cargos"""
        
        cargos = self.gerenciador.get_cargos(ctx.guild)
        
        embed = discord.Embed(
            title="📊 Ordem Hierárquica dos Cargos",
            description=f"**{len(cargos)}** cargos na hierarquia",
            color=discord.Color.blue()
        )
        
        lista = []
        for i, cargo in enumerate(cargos[:15], 1):
            lista.append(f"`#{i}` {cargo.mention}")
        
        embed.add_field(name="📌 Ordem (do mais alto para o mais baixo)", value="\n".join(lista), inline=False)
        
        if len(cargos) > 15:
            embed.set_footer(text=f"Mostrando 15 de {len(cargos)} cargos")
        
        await ctx.send(embed=embed)

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(CargosServidorCog(bot))
    print("✅ Sistema de Cargos do Servidor configurado!")
