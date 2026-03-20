from datetime import datetime
import discord
from discord.ext import commands
from discord import app_commands
import os
import sys
import asyncio
import aiohttp
from aiohttp import web
import socket
import traceback

# ==================== VERIFICAÇÃO DE INSTÂNCIA ÚNICA ====================
def verificar_instancia_unica():
    try:
        if sys.platform == "win32":
            import win32event, win32api, winerror
            mutex_name = "Bot_Jugadores_Unico"
            mutex = win32event.CreateMutex(None, False, mutex_name)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                print("❌ ERRO: Já existe uma instância do bot rodando!")
                return False
            return True
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind('\0bot_jugadores_unico')
            return True
    except Exception:
        return True

if not verificar_instancia_unica():
    sys.exit(1)

# ==================== CONFIGURAÇÕES ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True

class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        self.voz_conectada = False
        self.canal_voz_alvo = "💜・𝐖𝐚𝐯𝐞𝐗"
    
    async def setup_hook(self):
        """Registra comandos slash VAZIOS (só para aparecer o símbolo)"""
        print("🔄 Registrando comandos slash...")
        
        # NÃO registrar NENHUM comando slash - apenas manter vazio
        # Isso faz o bot aparecer na lista de slash commands
        # mas sem nenhum comando para mostrar
        
        print("✅ Bot configurado (sem comandos slash visíveis)")
    
    async def conectar_ao_canal_voz(self):
        """Conecta ao canal de voz automaticamente"""
        print("\n🔊 CONECTANDO AO CANAL DE VOZ...")
        
        if not self.guilds:
            print("❌ Bot não está em nenhum servidor")
            return None
        
        for guild in self.guilds:
            for channel in guild.voice_channels:
                if self.canal_voz_alvo in channel.name or channel.name in self.canal_voz_alvo:
                    print(f"✅ Canal encontrado: {channel.name}")
                    
                    if not channel.permissions_for(guild.me).connect:
                        print(f"❌ Sem permissão para conectar")
                        continue
                    
                    try:
                        for voz in self.voice_clients:
                            if voz.guild == guild:
                                await voz.disconnect()
                        
                        voz = await channel.connect()
                        self.voz_conectada = True
                        print(f"✅ CONECTADO com sucesso!")
                        return voz
                    except Exception as e:
                        print(f"❌ Erro: {e}")
            
            print(f"❌ Canal '{self.canal_voz_alvo}' não encontrado em {guild.name}")
        
        return None

bot = MeuBot()

# ==================== KEEP-ALIVE ====================
class KeepAliveServer:
    def __init__(self):
        self.app = None
        self.runner = None
    
    async def start(self):
        try:
            self.app = web.Application()
            
            async def handle(request):
                return web.Response(text="✅ Bot Online - Use !help")
            
            self.app.router.add_get('/', handle)
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            port = int(os.getenv('PORT', 8080))
            site = web.TCPSite(self.runner, '0.0.0.0', port)
            await site.start()
            print(f"🌐 Keep-alive na porta {port}")
        except Exception as e:
            print(f"⚠️ Erro: {e}")
    
    async def stop(self):
        if self.runner:
            await self.runner.cleanup()

keep_alive = KeepAliveServer()

# ==================== COMANDOS COM PREFIXO ! ====================

@bot.command(name="help")
async def help_command(ctx):
    """!help - Mostra todos os comandos"""
    embed = discord.Embed(
        title="🤖 Comandos do Bot",
        description="Lista de todos os comandos disponíveis:",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📌 Comandos",
        value="`!help` - Mostra esta mensagem\n"
              "`!ping` - Verifica latência\n"
              "`!status` - Status do bot\n"
              "`!info` - Informações\n"
              "`!tickets` - Sistema de tickets\n"
              "`!sets` - Sistema de sets\n"
              "`!cargos` - Lista cargos\n"
              "`!fixnick` - Corrige nickname\n"
              "`!voz` - Conecta/desconecta da voz",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name="ping")
async def ping_command(ctx):
    """!ping - Verifica latência"""
    latency = round(bot.latency * 1000)
    await ctx.send(f"🏓 Pong! `{latency}ms`")

@bot.command(name="status")
async def status_command(ctx):
    """!status - Status do bot"""
    embed = discord.Embed(
        title="📊 Status do Bot",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🤖 Nome", value=bot.user.name, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="🔊 Voz", value="✅" if bot.voz_conectada else "❌", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="info")
async def info_command(ctx):
    """!info - Informações do bot"""
    embed = discord.Embed(
        title="ℹ️ Sobre o Bot",
        description="Bot para comunidade Jugadores",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="📌 Versão", value="1.0.0", inline=True)
    embed.add_field(name="📚 Biblioteca", value=f"discord.py {discord.__version__}", inline=True)
    embed.add_field(name="⚙️ Prefixo", value="`!`", inline=True)
    
    await ctx.send(embed=embed)

@bot.command(name="tickets")
async def tickets_command(ctx):
    """!tickets - Sistema de tickets"""
    await ctx.send("🎫 Sistema de tickets (em desenvolvimento)")

@bot.command(name="sets")
async def sets_command(ctx):
    """!sets - Sistema de sets"""
    await ctx.send("🎮 Sistema de sets (em desenvolvimento)")

@bot.command(name="cargos")
async def cargos_command(ctx):
    """!cargos - Lista todos os cargos"""
    cargos = [role for role in ctx.guild.roles if role.name != "@everyone"]
    cargos.sort(key=lambda r: r.position, reverse=True)
    
    embed = discord.Embed(
        title="📋 Cargos do Servidor",
        description=f"Total: **{len(cargos)}** cargos",
        color=discord.Color.blue()
    )
    
    lista = []
    for i, cargo in enumerate(cargos[:20], 1):
        lista.append(f"`{i:02d}.` {cargo.mention}")
    
    embed.add_field(name="📌 Lista", value="\n".join(lista), inline=False)
    
    if len(cargos) > 20:
        embed.set_footer(text=f"Mostrando 20 de {len(cargos)} cargos")
    
    await ctx.send(embed=embed)

@bot.command(name="fixnick")
async def fixnick_command(ctx, member: discord.Member = None):
    """!fixnick - Corrige nickname"""
    target = member or ctx.author
    
    if target != ctx.author and not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Você não tem permissão para corrigir nickname de outros!")
        return
    
    await ctx.send(f"🔄 Corrigindo nickname de {target.mention}... (em desenvolvimento)")

@bot.command(name="voz")
async def voz_command(ctx):
    """!voz - Conecta/desconecta da voz"""
    
    if ctx.author.voice is None:
        await ctx.send("❌ Você precisa estar em um canal de voz para usar este comando!")
        return
    
    # Verificar se já está conectado
    if ctx.guild.voice_client:
        await ctx.guild.voice_client.disconnect()
        bot.voz_conectada = False
        await ctx.send("🔇 Desconectado do canal de voz!")
    else:
        try:
            await ctx.author.voice.channel.connect()
            bot.voz_conectada = True
            await ctx.send(f"🔊 Conectado ao canal {ctx.author.voice.channel.mention}!")
        except Exception as e:
            await ctx.send(f"❌ Erro: {e}")

# ==================== COMANDOS ADMIN ====================

@bot.command(name="sync")
@commands.has_permissions(administrator=True)
async def sync_command(ctx):
    """!sync - Sincroniza comandos (admin)"""
    await ctx.send("🔄 Comandos slash sincronizados!")
    # Não faz nada com slash commands para manter vazio

# ==================== EVENTOS ====================
@bot.event
async def on_ready():
    print("\n" + "="*60)
    print("✅ BOT CONECTADO!")
    print("="*60)
    print(f"🤖 Nome: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📡 Ping: {round(bot.latency * 1000)}ms")
    print(f"🏠 Servidores: {len(bot.guilds)}")
    print(f"📋 Comandos com prefixo: {len(bot.commands)}")
    print("="*60)
    
    # Listar servidores
    print("\n📋 Servidores:")
    for guild in bot.guilds:
        print(f"   • {guild.name} - {guild.member_count} membros")
    
    # Conectar à voz
    print("\n🔊 Verificando canal de voz...")
    await asyncio.sleep(2)
    await bot.conectar_ao_canal_voz()
    
    # Status personalizado
    status = f"!help | {len(bot.guilds)} servers"
    if bot.voz_conectada:
        status += " | 🔊"
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=status
        )
    )
    
    print("\n" + "="*60)
    print("🚀 BOT PRONTO! Use !help")
    print("="*60)

@bot.event
async def on_guild_join(guild):
    """Quando entra em um servidor"""
    print(f"\n📥 Entrou em: {guild.name}")
    
    # Tentar conectar à voz
    if not bot.voz_conectada:
        await bot.conectar_ao_canal_voz()
    
    # Mensagem de boas-vindas
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description="Use **!help** para ver todos os comandos!",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            break

@bot.event
async def on_voice_state_update(member, before, after):
    """Monitora voz"""
    if member == bot.user:
        if after.channel is None:
            bot.voz_conectada = False
            print(f"🔇 Desconectado de {before.channel.guild.name}")
            
            await asyncio.sleep(5)
            if not bot.voz_conectada:
                await bot.conectar_ao_canal_voz()

@bot.event
async def on_command_error(ctx, error):
    """Trata erros de comando"""
    if isinstance(error, commands.CommandNotFound):
        return
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Você não tem permissão para usar este comando!")
    else:
        await ctx.send(f"❌ Erro: {error}")

# ==================== CARREGAR MÓDULOS ====================
async def carregar_modulos():
    """Carrega módulos externos"""
    print("\n" + "="*60)
    print("📦 CARREGANDO MÓDULOS")
    print("="*60)
    
    modulos = [
        'modules.cargos_serv',
    ]
    
    for modulo in modulos:
        try:
            await bot.load_extension(modulo)
            print(f"   ✅ {modulo}")
        except FileNotFoundError:
            print(f"   ⚠️ {modulo} não encontrado")
        except Exception as e:
            print(f"   ⚠️ {modulo}: {e}")

# ==================== FUNÇÃO PRINCIPAL ====================
async def main():
    print("\n" + "="*60)
    print("🚀 INICIANDO BOT")
    print("="*60)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ Token não encontrado!")
        sys.exit(1)
    
    try:
        await keep_alive.start()
    except:
        pass
    
    await carregar_modulos()
    
    try:
        async with bot:
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n👋 Encerrando...")
    finally:
        for voz in bot.voice_clients:
            await voz.disconnect()
        await keep_alive.stop()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até mais!")
