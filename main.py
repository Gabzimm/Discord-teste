from datetime import datetime
import discord
from discord.ext import commands
import os
import sys
import asyncio
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
        
        self.canal_voz_id = 1479257448010350673  # ID do canal WaveX
        self.voz_conectada = False
    
    async def conectar_ao_canal_voz(self):
        """Conecta automaticamente ao canal de voz ao iniciar"""
        if not self.guilds:
            return None
        
        for guild in self.guilds:
            canal = guild.get_channel(self.canal_voz_id)
            if canal:
                try:
                    for voz in self.voice_clients:
                        if voz.guild == guild:
                            await voz.disconnect()
                            await asyncio.sleep(1)
                    
                    voz = await canal.connect()
                    self.voz_conectada = True
                    print(f"✅ Conectado ao canal {canal.name} em {guild.name}")
                    return voz
                except Exception as e:
                    print(f"❌ Erro ao conectar: {e}")
        
        print("❌ Canal WaveX não encontrado!")
        return None

bot = MeuBot()

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
              "`!info` - Informações do bot",
        inline=False
    )
    
    embed.add_field(
        name="🎮 Comandos de Cargos",
        value="`!cargos` - Lista todos os cargos do servidor",
        inline=False
    )
    
    embed.add_field(
        name="🔊 Comandos de Voz",
        value="`!entrar` - Entra na call WaveX\n"
              "`!sair` - Sai da call\n"
              "`!call` - Mostra status da call",
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
    embed.add_field(name="🆔 ID", value=bot.user.id, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    
    if ctx.voice_client and ctx.voice_client.is_connected():
        embed.add_field(name="🔊 Voz", value=f"✅ Conectado em {ctx.voice_client.channel.name}", inline=False)
    else:
        embed.add_field(name="🔊 Voz", value="❌ Desconectado", inline=False)
    
    await ctx.send(embed=embed)

@bot.command(name="info")
async def info_command(ctx):
    """!info - Informações do bot"""
    embed = discord.Embed(
        title="ℹ️ Sobre o Bot",
        description="Bot desenvolvido para a comunidade Jugadores",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="📌 Versão", value="2.0.0", inline=True)
    embed.add_field(name="📚 Biblioteca", value=f"discord.py {discord.__version__}", inline=True)
    embed.add_field(name="⚙️ Prefixo", value="`!`", inline=True)
    
    await ctx.send(embed=embed)

# ==================== COMANDOS DE CARGO ====================

@bot.command(name="cargos")
async def cargos_command(ctx):
    """!cargos - Lista cargos do servidor"""
    
    cargos = [role for role in ctx.guild.roles if role.name != "@everyone"]
    cargos.sort(key=lambda r: r.position, reverse=True)
    
    if not cargos:
        await ctx.send("❌ Nenhum cargo encontrado!")
        return
    
    embed = discord.Embed(
        title="📋 Cargos do Servidor",
        description=f"Total de **{len(cargos)}** cargos encontrados",
        color=discord.Color.blue()
    )
    
    lista = []
    for i, cargo in enumerate(cargos, 1):
        lista.append(f"`{i:02d}.` {cargo.mention} • Posição `#{i}` na hierarquia")
    
    for i in range(0, len(lista), 15):
        bloco = lista[i:i+15]
        embed.add_field(
            name="📌 Cargos (Ordem Hierárquica)",
            value="\n".join(bloco),
            inline=False
        )
    
    await ctx.send(embed=embed)

# ==================== COMANDOS DE VOZ ====================

@bot.command(name="entrar")
async def entrar_call(ctx):
    """!entrar - Entra na call WaveX"""
    
    canal = ctx.guild.get_channel(bot.canal_voz_id)
    
    if not canal:
        await ctx.send("❌ Canal WaveX não encontrado!")
        return
    
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await asyncio.sleep(1)
    
    try:
        await canal.connect()
        bot.voz_conectada = True
        await ctx.send(f"✅ Conectado ao canal **{canal.name}**!")
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@bot.command(name="sair")
async def sair_call(ctx):
    """!sair - Sai da call"""
    
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        bot.voz_conectada = False
        await ctx.send("✅ Desconectado!")
    else:
        await ctx.send("❌ Não estou em nenhum canal!")

@bot.command(name="call")
async def call_status(ctx):
    """!call - Mostra status da call"""
    
    if ctx.voice_client and ctx.voice_client.is_connected():
        await ctx.send(f"✅ Conectado em: {ctx.voice_client.channel.mention}")
    else:
        await ctx.send("❌ Desconectado")

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
    print("="*60)
    
    print("\n📋 Servidores conectados:")
    for i, guild in enumerate(bot.guilds, 1):
        print(f"   {i}. {guild.name} - {guild.member_count} membros")
    
    print("\n🔊 Tentando conectar ao canal WaveX...")
    await asyncio.sleep(2)
    await bot.conectar_ao_canal_voz()
    
    status = f"!help | {len(bot.guilds)} servers"
    if bot.voz_conectada:
        status += " | 🔊"
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=status
        )
    )
    
    print("\n🚀 BOT PRONTO! Use !help")
    print("="*60)

@bot.event
async def on_guild_join(guild):
    print(f"\n📥 Entrou no servidor: {guild.name}")
    
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
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    else:
        await ctx.send(f"❌ Erro: {error}")

# ==================== CARREGAR MÓDULOS ====================
async def carregar_modulos():
    print("\n" + "="*60)
    print("📦 CARREGANDO MÓDULOS")
    print("="*60)
    
    modulos = [
        'modules.cargos_serv',
        'modules.voz',
    ]
    
    for modulo in modulos:
        try:
            await bot.load_extension(modulo)
            print(f"   ✅ {modulo}")
        except Exception as e:
            print(f"   ⚠️ {modulo}: {e}")

# ==================== FUNÇÃO PRINCIPAL ====================
async def main():
    print("\n" + "="*60)
    print("🚀 INICIANDO BOT DISCORD")
    print("="*60)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        sys.exit(1)
    
    await carregar_modulos()
    
    try:
        async with bot:
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        traceback.print_exc()
    finally:
        for voz in bot.voice_clients:
            await voz.disconnect()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até mais!")
