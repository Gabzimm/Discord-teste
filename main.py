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
    except Exception as e:
        if sys.platform != "win32" and isinstance(e, socket.error):
            print("❌ ERRO: Já existe uma instância do bot rodando!")
            return False
        return True

if not verificar_instancia_unica():
    sys.exit(1)

# ==================== CONFIGURAÇÕES ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
    
    async def setup_hook(self):
        """Sincroniza os comandos quando o bot inicia"""
        print("🔄 Sincronizando comandos...")
        
        # SINCRONIZAÇÃO GLOBAL - TODOS OS COMANDOS APARECERÃO
        try:
            # Comandos globais (aparecem em todos os servidores)
            comandos = await self.tree.sync()
            print(f"✅ {len(comandos)} comandos sincronizados GLOBALMENTE!")
            
            # Listar comandos sincronizados
            for cmd in comandos:
                print(f"   → /{cmd.name}")
                
        except Exception as e:
            print(f"❌ Erro na sincronização global: {e}")
            
            # TENTATIVA 2: Sincronizar com um servidor específico (mais rápido)
            try:
                # Use um ID de servidor para testes (substitua pelo ID do seu servidor)
                # guild = discord.Object(id=SEU_ID_DO_SERVIDOR_AQUI)  # ← COLOQUE AQUI
                # comandos = await self.tree.sync(guild=guild)
                # print(f"✅ {len(comandos)} comandos sincronizados no servidor de teste!")
                pass
            except:
                pass

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
                return web.Response(
                    text="✅ Bot Online - Slash Commands Ativos!\nDigite / no Discord para ver os comandos.",
                    content_type='text/plain'
                )
            
            self.app.router.add_get('/', handle)
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            port = int(os.getenv('PORT', 8080))
            site = web.TCPSite(self.runner, '0.0.0.0', port)
            await site.start()
            
            print(f"🌐 Keep-alive na porta {port}")
            
        except Exception as e:
            print(f"⚠️ Erro keep-alive: {e}")
    
    async def stop(self):
        if self.runner:
            await self.runner.cleanup()

keep_alive = KeepAliveServer()

# ==================== SLASH COMMANDS ====================
# TODOS OS COMANDOS ABAIXO APARECERÃO NO /

@bot.tree.command(name="help", description="📖 Mostra todos os comandos disponíveis")
async def help_slash(interaction: discord.Interaction):
    """Comando /help"""
    embed = discord.Embed(
        title="🤖 Comandos Disponíveis",
        description="Lista de todos os comandos:",
        color=discord.Color.blue()
    )
    
    # Listar todos os comandos registrados
    comandos = bot.tree.get_commands()
    lista_comandos = []
    for cmd in comandos:
        lista_comandos.append(f"`/{cmd.name}` - {cmd.description}")
    
    embed.add_field(
        name="📋 Comandos",
        value="\n".join(lista_comandos),
        inline=False
    )
    
    embed.set_footer(text=f"Total: {len(comandos)} comandos")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="🏓 Verifica a latência do bot")
async def ping_slash(interaction: discord.Interaction):
    """Comando /ping"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! Latência: **{latency}ms**")

@bot.tree.command(name="status", description="📊 Mostra o status do bot")
async def status_slash(interaction: discord.Interaction):
    """Comando /status"""
    embed = discord.Embed(
        title="📊 Status do Bot",
        color=discord.Color.green()
    )
    
    embed.add_field(name="🤖 Nome", value=bot.user.name, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info", description="ℹ️ Informações sobre o bot")
async def info_slash(interaction: discord.Interaction):
    """Comando /info"""
    embed = discord.Embed(
        title="ℹ️ Sobre o Bot",
        description="Bot para comunidade Jugadores",
        color=discord.Color.purple()
    )
    
    embed.add_field(name="📌 Versão", value="1.0.0", inline=True)
    embed.add_field(name="⚙️ Tipo", value="Slash Commands", inline=True)
    
    await interaction.response.send_message(embed=embed)

# EXEMPLO DE COMANDO /sets
@bot.tree.command(name="sets", description="🎮 Sistema de sets")
async def sets_slash(interaction: discord.Interaction):
    """Comando /sets"""
    await interaction.response.send_message("🎮 Comando /sets executado!")

# EXEMPLO DE COMANDO /tickets
@bot.tree.command(name="tickets", description="🎫 Sistema de tickets")
async def tickets_slash(interaction: discord.Interaction):
    """Comando /tickets"""
    await interaction.response.send_message("🎫 Comando /tickets executado!")

# EXEMPLO DE COMANDO /cargos
@bot.tree.command(name="cargos", description="⚙️ Sistema de cargos")
async def cargos_slash(interaction: discord.Interaction):
    """Comando /cargos"""
    await interaction.response.send_message("⚙️ Comando /cargos executado!")

# EXEMPLO DE COMANDO /premios
@bot.tree.command(name="premios", description="🏆 Sistema de prêmios")
async def premios_slash(interaction: discord.Interaction):
    """Comando /premios"""
    await interaction.response.send_message("🏆 Comando /premios executado!")

# ==================== EVENTOS ====================
@bot.event
async def on_ready():
    print("\n" + "="*50)
    print("✅ BOT CONECTADO!")
    print("="*50)
    print(f"🤖 Nome: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"🏠 Servidores: {len(bot.guilds)}")
    print(f"📊 Comandos Registrados: {len(bot.tree.get_commands())}")
    print("="*50)
    
    # Mostrar comandos registrados
    print("\n📋 Comandos disponíveis:")
    for cmd in bot.tree.get_commands():
        print(f"   → /{cmd.name}")
    
    print("\n💡 Digite / no Discord para ver os comandos!")
    
    # Status personalizado
    await bot.change_presence(
        activity=discord.Game(name=f"/help | {len(bot.guilds)} servidores")
    )

@bot.event
async def on_guild_join(guild):
    """Quando entra em um novo servidor"""
    print(f"📥 Entrei no servidor: {guild.name}")
    
    # Tenta enviar mensagem de boas-vindas
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description=(
                    f"**Comandos disponíveis:**\n"
                    f"Digite **/** no chat para ver todos os comandos!\n\n"
                    f"📝 **Principais comandos:**\n"
                    f"• `/help` - Ver todos os comandos\n"
                    f"• `/ping` - Verificar latência\n"
                    f"• `/status` - Status do bot"
                ),
                color=discord.Color.green()
            )
            await channel.send(embed=embed)
            break

# ==================== TRATAMENTO DE ERROS ====================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Trata erros dos slash commands"""
    if isinstance(error, app_commands.CommandNotFound):
        await interaction.response.send_message("❌ Comando não encontrado!", ephemeral=True)
    else:
        print(f"❌ Erro: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Erro: {error}", ephemeral=True)

# ==================== FUNÇÃO PRINCIPAL ====================
async def load_modules():
    """Carrega os módulos (se existirem)"""
    modulos = [
        'modules.sets',
        'modules.tickets',
        'modules.cargos',
        'modules.premios',
    ]
    
    for modulo in modulos:
        try:
            await bot.load_extension(modulo)
            print(f"✅ Módulo carregado: {modulo}")
        except Exception as e:
            print(f"⚠️ Módulo não carregado: {modulo} - {e}")

async def main():
    print("\n" + "="*50)
    print("🚀 INICIANDO BOT")
    print("="*50)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ DISCORD_TOKEN não encontrado!")
        sys.exit(1)
    
    # Iniciar keep-alive
    await keep_alive.start()
    
    # Carregar módulos
    await load_modules()
    
    # Conectar ao Discord
    try:
        async with bot:
            await bot.start(TOKEN)
    except KeyboardInterrupt:
        print("\n👋 Bot encerrado")
    finally:
        await keep_alive.stop()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até mais!")
