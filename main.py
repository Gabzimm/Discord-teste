from datetime import datetime
import discord
from discord.ext import commands
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
    
    async def setup_hook(self):
        """Carrega os módulos quando o bot inicia"""
        print("🔄 Carregando módulos...")

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

# ==================== COMANDOS PRINCIPAIS ====================

@bot.command(name="help")
async def help_command(ctx):
    """!help - Mostra todos os comandos"""
    embed = discord.Embed(
        title="🤖 Comandos do Bot",
        description="Lista de todos os comandos disponíveis:",
        color=discord.Color.purple()
    )
    
    embed.add_field(
        name="📌 Comandos Gerais",
        value="`!help` - Mostra esta mensagem\n"
              "`!ping` - Verifica latência\n"
              "`!status` - Status do bot\n"
              "`!info` - Informações",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Sistema de Cargos",
        value="`!cargos` - Lista todos os cargos\n"
              "`!cargos_parar` - Para atualização\n"
              "`!cargos_atualizar` - Força atualização",
        inline=False
    )
    
    embed.add_field(
        name="🔊 Sistema de Voz",
        value="`!voz_conectar` - Conecta à call\n"
              "`!voz_desconectar` - Desconecta\n"
              "`!voz_status` - Status da voz\n"
              "`!voz_reconectar` - Reconecta",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Outros Sistemas",
        value="`!sets` - Sistema de sets\n"
              "`!tickets` - Sistema de tickets\n"
              "`!fixnick` - Corrige nickname",
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
    
    # Verificar status da voz
    voz_status = "❌ Desconectado"
    for voz in bot.voice_clients:
        if voz.is_connected():
            voz_status = f"✅ Conectado em {voz.channel.name}"
            break
    
    embed = discord.Embed(
        title="📊 Status do Bot",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🤖 Nome", value=bot.user.name, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="🔊 Voz", value=voz_status, inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="info")
async def info_command(ctx):
    """!info - Informações do bot"""
    embed = discord.Embed(
        title="ℹ️ Sobre o Bot",
        description="Bot para comunidade Jugadores",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="📌 Versão", value="2.0.0", inline=True)
    embed.add_field(name="📚 Biblioteca", value=f"discord.py {discord.__version__}", inline=True)
    embed.add_field(name="⚙️ Prefixo", value="`!`", inline=True)
    
    await ctx.send(embed=embed)

# ==================== COMANDOS EXEMPLO ====================

@bot.command(name="sets")
async def sets_command(ctx):
    """!sets - Sistema de sets"""
    await ctx.send("🎮 Sistema de sets (em desenvolvimento)")

@bot.command(name="tickets")
async def tickets_command(ctx):
    """!tickets - Sistema de tickets"""
    await ctx.send("🎫 Sistema de tickets (em desenvolvimento)")

@bot.command(name="fixnick")
async def fixnick_command(ctx, member: discord.Member = None):
    """!fixnick - Corrige nickname"""
    target = member or ctx.author
    
    if target != ctx.author and not ctx.author.guild_permissions.administrator:
        await ctx.send("❌ Você não tem permissão para corrigir nickname de outros!")
        return
    
    await ctx.send(f"🔄 Corrigindo nickname de {target.mention}... (em desenvolvimento)")

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
    print(f"📋 Comandos: {len(bot.commands)}")
    print("="*60)
    
    # Listar servidores
    print("\n📋 Servidores:")
    for guild in bot.guilds:
        print(f"   • {guild.name} - {guild.member_count} membros")
    
    # Status
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=f"!help | {len(bot.guilds)} servers"
        )
    )
    
    print("\n🚀 BOT PRONTO! Use !help")
    print("="*60)

@bot.event
async def on_guild_join(guild):
    """Quando entra em um servidor"""
    print(f"\n📥 Entrou em: {guild.name}")
    
    # Mensagem de boas-vindas
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description="**WaveX** Os melhores preços!",
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            break

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
    """Carrega todos os módulos"""
    print("\n" + "="*60)
    print("📦 CARREGANDO MÓDULOS")
    print("="*60)
    
    modulos = [
        'modules.cargos_serv',
        'modules.voz',  # ← NOVO MÓDULO DE VOZ
    ]
    
    for modulo in modulos:
        try:
            await bot.load_extension(modulo)
            print(f"   ✅ {modulo}")
        except Exception as e:
            print(f"   ❌ {modulo}: {e}")
    
    print("="*60)

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
        # Desconectar da voz
        for voz in bot.voice_clients:
            await voz.disconnect()
        await keep_alive.stop()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até mais!")
