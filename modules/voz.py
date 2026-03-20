import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime

class VozCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voz_conectada = False
        self.canal_voz_alvo = "💜・𝐖𝐚𝐯𝐞𝐗"
        self.tentativas_reconexao = 0
        self.max_tentativas = 5
        
        # Iniciar tarefa de verificação de voz
        self.verificar_voz.start()
        
        print("🔊 Sistema de Voz carregado!")
    
    def cog_unload(self):
        """Quando o cog é descarregado"""
        self.verificar_voz.cancel()
        print("🔊 Sistema de Voz descarregado")
    
    @tasks.loop(minutes=1.0)
    async def verificar_voz(self):
        """Verifica periodicamente se o bot está na call"""
        if not self.bot.is_ready():
            return
        
        # Se já está conectado, verificar se ainda está
        if self.bot.voice_clients:
            for voz in self.bot.voice_clients:
                if voz.is_connected():
                    self.voz_conectada = True
                    self.tentativas_reconexao = 0
                    return
        
        # Se não está conectado, tentar conectar
        if not self.voz_conectada:
            print("🔊 Verificando conexão de voz...")
            await self.conectar_automatico()
    
    @verificar_voz.before_loop
    async def before_verificar_voz(self):
        """Aguardar bot estar pronto"""
        await self.bot.wait_until_ready()
        print("✅ Verificação de voz iniciada!")
    
    async def conectar_automatico(self):
        """Conecta automaticamente ao canal de voz"""
        
        if not self.bot.guilds:
            print("❌ Bot não está em nenhum servidor")
            return False
        
        for guild in self.bot.guilds:
            print(f"\n🔍 Procurando canal em: {guild.name}")
            
            # Listar canais de voz do servidor
            canais_voz = guild.voice_channels
            if not canais_voz:
                print(f"   ❌ Nenhum canal de voz em {guild.name}")
                continue
            
            # Procurar canal alvo
            canal_encontrado = None
            for channel in canais_voz:
                # Verificar nome exato ou aproximado
                if self.canal_voz_alvo in channel.name or channel.name in self.canal_voz_alvo:
                    canal_encontrado = channel
                    print(f"   ✅ Canal encontrado: {channel.name}")
                    break
            
            if not canal_encontrado:
                print(f"   ❌ Canal '{self.canal_voz_alvo}' não encontrado")
                continue
            
            # Verificar permissões
            permissoes = canal_encontrado.permissions_for(guild.me)
            if not permissoes.connect:
                print(f"   ❌ Sem permissão CONNECT em {canal_encontrado.name}")
                continue
            
            # Desconectar se já estiver em outro canal
            for voz in self.bot.voice_clients:
                if voz.guild == guild:
                    await voz.disconnect()
                    print(f"   🔄 Desconectado de canal anterior")
            
            try:
                # Conectar
                voz = await canal_encontrado.connect()
                self.voz_conectada = True
                self.tentativas_reconexao = 0
                print(f"\n✅ CONECTADO com sucesso em {canal_encontrado.name} ({guild.name})")
                
                # Atualizar status
                await self.bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.playing,
                        name=f"!help | 🔊 {canal_encontrado.name}"
                    )
                )
                
                return True
                
            except Exception as e:
                print(f"   ❌ Erro ao conectar: {e}")
                self.tentativas_reconexao += 1
                
                if self.tentativas_reconexao >= self.max_tentativas:
                    print(f"   ⚠️ Máximo de tentativas ({self.max_tentativas}) atingido!")
                    self.tentativas_reconexao = 0
                    return False
        
        print("\n❌ NÃO FOI POSSÍVEL CONECTAR A NENHUM CANAL")
        return False
    
    async def desconectar(self):
        """Desconecta de todos os canais de voz"""
        desconectados = 0
        for voz in self.bot.voice_clients:
            await voz.disconnect()
            desconectados += 1
        
        self.voz_conectada = False
        print(f"🔇 Desconectado de {desconectados} canais")
        return desconectados
    
    # ===== COMANDOS COM PREFIXO ! =====
    
    @commands.command(name="voz_conectar")
    async def voz_conectar_comando(self, ctx):
        """!voz_conectar - Conecta manualmente ao canal de voz"""
        
        # Verificar se o usuário está em um canal
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando!")
            return
        
        try:
            # Conectar ao canal do usuário
            await ctx.author.voice.channel.connect()
            self.voz_conectada = True
            await ctx.send(f"✅ Conectado ao canal {ctx.author.voice.channel.mention}!")
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}")
    
    @commands.command(name="voz_desconectar")
    async def voz_desconectar_comando(self, ctx):
        """!voz_desconectar - Desconecta do canal de voz"""
        
        if not ctx.voice_client:
            await ctx.send("❌ Bot não está em nenhum canal de voz!")
            return
        
        await ctx.voice_client.disconnect()
        self.voz_conectada = False
        await ctx.send("✅ Desconectado do canal de voz!")
    
    @commands.command(name="voz_status")
    async def voz_status_comando(self, ctx):
        """!voz_status - Mostra status da conexão de voz"""
        
        embed = discord.Embed(
            title="🔊 Status da Voz",
            color=discord.Color.blue()
        )
        
        if ctx.voice_client and ctx.voice_client.is_connected():
            embed.add_field(
                name="✅ Conectado",
                value=f"Canal: {ctx.voice_client.channel.mention}\n"
                      f"Servidor: {ctx.guild.name}",
                inline=False
            )
        else:
            embed.add_field(name="❌ Status", value="Desconectado", inline=False)
        
        # Canais disponíveis
        canais = ctx.guild.voice_channels
        if canais:
            lista = []
            for c in canais[:10]:
                if self.canal_voz_alvo in c.name:
                    lista.append(f"🎯 {c.name}")
                else:
                    lista.append(f"   • {c.name}")
            
            embed.add_field(
                name=f"📋 Canais de Voz ({len(canais)})",
                value="\n".join(lista[:10]),
                inline=False
            )
        
        embed.add_field(
            name="🎯 Canal Alvo",
            value=f"`{self.canal_voz_alvo}`",
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="voz_reconectar")
    async def voz_reconectar_comando(self, ctx):
        """!voz_reconectar - Força reconexão ao canal alvo"""
        
        await ctx.send("🔄 Tentando reconectar...")
        
        # Desconectar se estiver conectado
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await asyncio.sleep(2)
        
        # Tentar conectar
        if await self.conectar_automatico():
            await ctx.send("✅ Reconectado com sucesso!")
        else:
            await ctx.send("❌ Falha na reconexão!")

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(VozCog(bot))
    print("✅ Sistema de Voz configurado!")
