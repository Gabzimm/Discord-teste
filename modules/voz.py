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
        
        print("\n" + "="*50)
        print("🔊 TENTANDO CONEXÃO AUTOMÁTICA")
        print("="*50)
        
        if not self.bot.guilds:
            print("❌ Bot não está em nenhum servidor")
            return False
        
        for guild in self.bot.guilds:
            print(f"\n📋 Servidor: {guild.name}")
            
            # Listar todos os canais de voz
            canais_voz = guild.voice_channels
            if not canais_voz:
                print(f"   ❌ Nenhum canal de voz encontrado")
                continue
            
            print(f"   🎤 Canais disponíveis: {len(canais_voz)}")
            for c in canais_voz:
                print(f"      • {c.name}")
            
            # Procurar canal alvo (ignorando formatação)
            canal_encontrado = None
            for channel in canais_voz:
                # Comparar ignorando caracteres especiais e formatação
                nome_canal = channel.name
                nome_alvo = self.canal_voz_alvo
                
                # Verificar se o nome contém "WaveX" ou "𝐖𝐚𝐯𝐞𝐗"
                if "WaveX" in nome_canal or "𝐖𝐚𝐯𝐞𝐗" in nome_canal:
                    canal_encontrado = channel
                    print(f"   ✅ Canal encontrado: {channel.name}")
                    break
                
                # Verificar nome exato
                if nome_canal == nome_alvo:
                    canal_encontrado = channel
                    print(f"   ✅ Canal encontrado: {channel.name}")
                    break
            
            if not canal_encontrado:
                print(f"   ❌ Canal com 'WaveX' não encontrado")
                continue
            
            # Verificar permissões
            permissoes = canal_encontrado.permissions_for(guild.me)
            print(f"   🔐 Permissões:")
            print(f"      • Conectar: {'✅' if permissoes.connect else '❌'}")
            print(f"      • Falar: {'✅' if permissoes.speak else '❌'}")
            
            if not permissoes.connect:
                print(f"   ❌ Sem permissão CONNECT")
                continue
            
            # Desconectar se já estiver em outro canal
            for voz in self.bot.voice_clients:
                if voz.guild == guild:
                    await voz.disconnect()
                    print(f"   🔄 Desconectado de canal anterior")
                    await asyncio.sleep(1)
            
            try:
                # Conectar
                print(f"   🔌 Conectando a {canal_encontrado.name}...")
                voz = await canal_encontrado.connect(timeout=10.0, reconnect=True)
                self.voz_conectada = True
                self.tentativas_reconexao = 0
                print(f"\n✅ CONECTADO com sucesso!")
                print(f"   📌 Canal: {canal_encontrado.name}")
                print(f"   🏠 Servidor: {guild.name}")
                
                # Atualizar status
                await self.bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.playing,
                        name=f"!help | 🔊 {canal_encontrado.name}"
                    )
                )
                
                return True
                
            except discord.errors.ClientException as e:
                print(f"   ❌ Já conectado em outro lugar: {e}")
            except asyncio.TimeoutError:
                print(f"   ❌ Timeout ao conectar")
                self.tentativas_reconexao += 1
            except Exception as e:
                print(f"   ❌ Erro: {type(e).__name__} - {e}")
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
        """!voz_conectar - Conecta ao canal de voz"""
        
        await ctx.send("🔊 Tentando conectar...")
        
        # Tentar conectar automaticamente
        if await self.conectar_automatico():
            await ctx.send("✅ Conectado com sucesso!")
        else:
            # Se falhou, tentar conectar ao canal onde o usuário está
            if ctx.author.voice:
                canal = ctx.author.voice.channel
                try:
                    await canal.connect()
                    self.voz_conectada = True
                    await ctx.send(f"✅ Conectado ao seu canal: {canal.mention}!")
                except Exception as e:
                    await ctx.send(f"❌ Falha na conexão: {e}")
            else:
                await ctx.send("❌ Falha na reconexão! Verifique se o canal '💜・𝐖𝐚𝐯𝐞𝐗' existe e se tenho permissão de conectar.")
    
    @commands.command(name="voz_desconectar")
    async def voz_desconectar_comando(self, ctx):
        """!voz_desconectar - Desconecta do canal de voz"""
        
        if not ctx.voice_client:
            await ctx.send("❌ Bot não está em nenhum canal de voz!")
            return
        
        canal_nome = ctx.voice_client.channel.name
        await ctx.voice_client.disconnect()
        self.voz_conectada = False
        await ctx.send(f"✅ Desconectado de {canal_nome}!")
    
    @commands.command(name="voz_status")
    async def voz_status_comando(self, ctx):
        """!voz_status - Mostra status da conexão de voz"""
        
        embed = discord.Embed(
            title="🔊 Status da Voz",
            color=discord.Color.blue()
        )
        
        # Status atual
        if ctx.voice_client and ctx.voice_client.is_connected():
            embed.add_field(
                name="✅ Conectado",
                value=f"Canal: {ctx.voice_client.channel.mention}\n"
                      f"Servidor: {ctx.guild.name}",
                inline=False
            )
        else:
            embed.add_field(name="❌ Status", value="Desconectado", inline=False)
        
        # Listar todos os canais de voz
        canais = ctx.guild.voice_channels
        if canais:
            lista = []
            for c in canais:
                # Verificar permissões
                permissoes = c.permissions_for(ctx.guild.me)
                status = "✅" if permissoes.connect else "❌"
                
                # Destacar canal alvo
                if "WaveX" in c.name or "𝐖𝐚𝐯𝐞𝐗" in c.name:
                    lista.append(f"🎯 {status} {c.name}")
                else:
                    lista.append(f"   {status} {c.name}")
            
            embed.add_field(
                name=f"📋 Canais de Voz ({len(canais)})",
                value="\n".join(lista),
                inline=False
            )
        
        embed.add_field(
            name="🎯 Canal Alvo",
            value=f"`💜・𝐖𝐚𝐯𝐞𝐗` ou qualquer canal com 'WaveX' no nome",
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
            await ctx.send("❌ Falha na reconexão! Use `!voz_status` para ver os canais disponíveis.")
    
    @commands.command(name="voz_listar")
    async def voz_listar_comando(self, ctx):
        """!voz_listar - Lista todos os canais de voz disponíveis"""
        
        canais = ctx.guild.voice_channels
        
        if not canais:
            await ctx.send("❌ Nenhum canal de voz encontrado!")
            return
        
        embed = discord.Embed(
            title="🎤 Canais de Voz",
            description=f"Servidor: **{ctx.guild.name}**",
            color=discord.Color.blue()
        )
        
        lista = []
        for c in canais:
            permissoes = c.permissions_for(ctx.guild.me)
            status = "✅" if permissoes.connect else "❌"
            membros = len(c.members)
            lista.append(f"{status} **{c.name}** - {membros} membros")
        
        embed.add_field(
            name=f"Total: {len(canais)} canais",
            value="\n".join(lista),
            inline=False
        )
        
        await ctx.send(embed=embed)

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(VozCog(bot))
    print("✅ Sistema de Voz configurado!")
