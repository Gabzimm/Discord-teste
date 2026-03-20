import discord
from discord.ext import commands, tasks
import asyncio
from datetime import datetime

class VozCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.voz_conectada = False
        self.canal_voz_alvo = "WaveX"  # Nome do canal
        self.canal_voz_id = 1479257448010350673  # ID do canal WaveX
        self.tentativas_reconexao = 0
        self.max_tentativas = 5
        
        # Iniciar tarefa de verificação de voz
        self.verificar_voz.start()
        
        print("🔊 Sistema de Voz carregado!")
        print(f"🎯 Canal alvo: {self.canal_voz_alvo} (ID: {self.canal_voz_id})")
    
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
            await self.conectar_ao_canal_especifico()
    
    @verificar_voz.before_loop
    async def before_verificar_voz(self):
        """Aguardar bot estar pronto"""
        await self.bot.wait_until_ready()
        print("✅ Verificação de voz iniciada!")
    
    async def conectar_ao_canal_especifico(self):
        """Conecta diretamente ao canal WaveX pelo ID"""
        
        print("\n" + "="*50)
        print("🔊 TENTANDO CONEXÃO AO CANAL WaveX")
        print("="*50)
        
        if not self.bot.guilds:
            print("❌ Bot não está em nenhum servidor")
            return False
        
        for guild in self.bot.guilds:
            print(f"\n📋 Servidor: {guild.name}")
            
            # Procurar canal pelo ID
            canal = guild.get_channel(self.canal_voz_id)
            
            if not canal:
                # Se não encontrar pelo ID, procurar pelo nome
                for c in guild.voice_channels:
                    if c.name == self.canal_voz_alvo:
                        canal = c
                        print(f"   ✅ Canal encontrado pelo nome: {c.name}")
                        break
            
            if not canal:
                print(f"   ❌ Canal '{self.canal_voz_alvo}' não encontrado")
                continue
            
            print(f"   🎤 Canal encontrado: {canal.name} (ID: {canal.id})")
            
            # Verificar permissões
            permissoes = canal.permissions_for(guild.me)
            print(f"   🔐 Permissões:")
            print(f"      • Conectar: {'✅' if permissoes.connect else '❌'}")
            print(f"      • Falar: {'✅' if permissoes.speak else '❌'}")
            print(f"      • Ver Canal: {'✅' if permissoes.view_channel else '❌'}")
            
            if not permissoes.connect:
                print(f"   ❌ Sem permissão CONNECT")
                print(f"   💡 Dica: Dê permissão de 'Conectar' para o bot no canal {canal.name}")
                continue
            
            if not permissoes.view_channel:
                print(f"   ❌ Sem permissão para ver o canal")
                print(f"   💡 Dica: Dê permissão de 'Ver Canal' para o bot")
                continue
            
            # Desconectar se já estiver em outro canal
            for voz in self.bot.voice_clients:
                if voz.guild == guild:
                    await voz.disconnect()
                    print(f"   🔄 Desconectado de canal anterior")
                    await asyncio.sleep(1)
            
            try:
                # Tentar conectar
                print(f"   🔌 Conectando a {canal.name}...")
                voz = await canal.connect(timeout=10.0, reconnect=True)
                self.voz_conectada = True
                self.tentativas_reconexao = 0
                print(f"\n✅ CONECTADO com sucesso!")
                print(f"   📌 Canal: {canal.name}")
                print(f"   🏠 Servidor: {guild.name}")
                
                # Atualizar status
                await self.bot.change_presence(
                    activity=discord.Activity(
                        type=discord.ActivityType.playing,
                        name=f"!help | 🔊 {canal.name}"
                    )
                )
                
                return True
                
            except discord.errors.ClientException as e:
                print(f"   ❌ Já conectado em outro lugar: {e}")
            except asyncio.TimeoutError:
                print(f"   ❌ Timeout ao conectar")
                self.tentativas_reconexao += 1
            except discord.errors.Forbidden:
                print(f"   ❌ Acesso negado! Bot não tem permissão para entrar no canal")
                print(f"   💡 Dica: Verifique se o bot tem permissão de 'Conectar' e 'Ver Canal'")
            except Exception as e:
                print(f"   ❌ Erro: {type(e).__name__} - {e}")
                self.tentativas_reconexao += 1
                
                if self.tentativas_reconexao >= self.max_tentativas:
                    print(f"   ⚠️ Máximo de tentativas ({self.max_tentativas}) atingido!")
                    self.tentativas_reconexao = 0
                    return False
        
        print("\n❌ NÃO FOI POSSÍVEL CONECTAR")
        return False
    
    async def conectar_ao_canal_do_usuario(self, ctx):
        """Conecta ao canal onde o usuário está"""
        if not ctx.author.voice:
            return False
        
        canal = ctx.author.voice.channel
        
        try:
            # Desconectar se já estiver conectado
            if ctx.voice_client:
                await ctx.voice_client.disconnect()
                await asyncio.sleep(1)
            
            await canal.connect()
            self.voz_conectada = True
            return True
        except Exception as e:
            print(f"Erro ao conectar no canal do usuário: {e}")
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
        """!voz_conectar - Conecta ao canal WaveX"""
        
        await ctx.send("🔊 Tentando conectar ao canal WaveX...")
        
        # Tentar conectar ao canal WaveX
        if await self.conectar_ao_canal_especifico():
            await ctx.send("✅ Conectado ao canal WaveX com sucesso!")
        else:
            await ctx.send("❌ Falha na conexão! Use `!voz_debug` para verificar permissões.")
    
    @commands.command(name="voz_conectar_aqui")
    async def voz_conectar_aqui_comando(self, ctx):
        """!voz_conectar_aqui - Conecta ao canal onde você está"""
        
        if not ctx.author.voice:
            await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando!")
            return
        
        canal = ctx.author.voice.channel
        await ctx.send(f"🔊 Tentando conectar ao canal {canal.mention}...")
        
        if await self.conectar_ao_canal_do_usuario(ctx):
            await ctx.send(f"✅ Conectado ao seu canal: {canal.mention}!")
        else:
            await ctx.send("❌ Falha na conexão!")
    
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
        
        # Canal alvo
        embed.add_field(
            name="🎯 Canal Alvo",
            value=f"**WaveX** (ID: {self.canal_voz_id})",
            inline=False
        )
        
        # Listar todos os canais de voz
        canais = ctx.guild.voice_channels
        if canais:
            lista = []
            for c in canais:
                # Verificar permissões
                permissoes = c.permissions_for(ctx.guild.me)
                status = "✅" if permissoes.connect else "❌"
                
                # Destacar canal alvo
                if c.id == self.canal_voz_id:
                    lista.append(f"🎯 {status} **{c.name}** (ID: {c.id})")
                else:
                    lista.append(f"   {status} {c.name}")
            
            embed.add_field(
                name=f"📋 Canais de Voz ({len(canais)})",
                value="\n".join(lista),
                inline=False
            )
        
        await ctx.send(embed=embed)
    
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
            
            # Destacar canal WaveX
            if c.name == "WaveX" or c.id == self.canal_voz_id:
                lista.append(f"🎯 {status} **{c.name}** - {membros} membros (ID: {c.id})")
            else:
                lista.append(f"   {status} {c.name} - {membros} membros (ID: {c.id})")
        
        embed.add_field(
            name=f"Total: {len(canais)} canais",
            value="\n".join(lista),
            inline=False
        )
        
        await ctx.send(embed=embed)
    
    @commands.command(name="voz_reconectar")
    async def voz_reconectar_comando(self, ctx):
        """!voz_reconectar - Força reconexão ao canal WaveX"""
        
        await ctx.send("🔄 Tentando reconectar ao canal WaveX...")
        
        # Desconectar se estiver conectado
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await asyncio.sleep(2)
        
        # Tentar conectar
        if await self.conectar_ao_canal_especifico():
            await ctx.send("✅ Reconectado com sucesso!")
        else:
            await ctx.send("❌ Falha na reconexão! Use `!voz_debug` para verificar permissões.")
    
    @commands.command(name="voz_debug")
    async def voz_debug_comando(self, ctx):
        """!voz_debug - Diagnóstico completo da voz"""
        
        embed = discord.Embed(
            title="🔧 Diagnóstico de Voz",
            color=discord.Color.orange()
        )
        
        # 1. Servidor
        embed.add_field(name="📌 Servidor", value=ctx.guild.name, inline=False)
        
        # 2. Canal alvo
        canal_alvo = ctx.guild.get_channel(self.canal_voz_id)
        if canal_alvo:
            embed.add_field(
                name="🎯 Canal Alvo",
                value=f"**{canal_alvo.name}** (ID: {canal_alvo.id})\n"
                      f"Tipo: {type(canal_alvo).__name__}",
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Canal Alvo",
                value=f"Não encontrado! ID: {self.canal_voz_id}",
                inline=False
            )
        
        # 3. Canais de voz com permissões
        canais = ctx.guild.voice_channels
        if canais:
            lista = []
            for c in canais:
                permissoes = c.permissions_for(ctx.guild.me)
                connect = "✅" if permissoes.connect else "❌"
                view = "✅" if permissoes.view_channel else "❌"
                
                if c.id == self.canal_voz_id:
                    lista.append(f"🎯 **{c.name}**")
                    lista.append(f"   • Conectar: {connect}")
                    lista.append(f"   • Ver Canal: {view}")
                    lista.append(f"   • Membros: {len(c.members)}")
                    lista.append("")
                else:
                    lista.append(f"   • {c.name}: Conectar {connect}")
            
            embed.add_field(
                name=f"🎤 Detalhes dos Canais",
                value="\n".join(lista[:15]),
                inline=False
            )
        
        # 4. Permissões do bot
        permissoes = ctx.guild.me.guild_permissions
        embed.add_field(
            name="🔐 Permissões do Bot (Gerais)",
            value=f"Conectar: {'✅' if permissoes.connect else '❌'}\n"
                  f"Falar: {'✅' if permissoes.speak else '❌'}\n"
                  f"Mover Membros: {'✅' if permissoes.move_members else '❌'}\n"
                  f"Ver Canais: {'✅' if permissoes.view_channel else '❌'}",
            inline=False
        )
        
        # 5. Status atual
        if ctx.voice_client:
            embed.add_field(
                name="🔊 Status Atual",
                value=f"Conectado em: {ctx.voice_client.channel.name}",
                inline=False
            )
        else:
            embed.add_field(name="🔊 Status Atual", value="Desconectado", inline=False)
        
        await ctx.send(embed=embed)

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(VozCog(bot))
    print("✅ Sistema de Voz configurado!")
