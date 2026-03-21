from datetime import datetime
import discord
from discord.ext import commands
import os
import sys
import asyncio
import socket
import traceback
from aiohttp import web

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

bot = MeuBot()

# ==================== KEEP-ALIVE SERVER ====================
class KeepAliveServer:
    def __init__(self):
        self.app = None
        self.runner = None
        self.site = None
        self.bot = None
    
    async def start(self):
        try:
            self.app = web.Application()
            
            async def handle_home(request):
                html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>WaveX Bot - Status</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {{
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            margin: 0;
                            padding: 0;
                            min-height: 100vh;
                            display: flex;
                            justify-content: center;
                            align-items: center;
                        }}
                        .container {{
                            background: white;
                            border-radius: 20px;
                            padding: 40px;
                            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                            max-width: 600px;
                            width: 90%;
                            text-align: center;
                        }}
                        h1 {{ color: #667eea; margin-bottom: 10px; }}
                        .status {{ font-size: 18px; margin: 20px 0; padding: 15px; border-radius: 10px; background: #f0f0f0; }}
                        .online {{ color: #4CAF50; font-weight: bold; }}
                        .offline {{ color: #f44336; font-weight: bold; }}
                        .info {{ text-align: left; margin: 20px 0; padding: 15px; background: #e3f2fd; border-radius: 10px; }}
                        .commands {{ text-align: left; margin: 20px 0; padding: 15px; background: #f5f5f5; border-radius: 10px; }}
                        .commands code {{ background: #e0e0e0; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
                        footer {{ margin-top: 20px; color: #999; font-size: 12px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🤖 WaveX Bot</h1>
                        <div class="status">
                            Status: <span class="online">🟢 ONLINE</span>
                        </div>
                        <div class="info">
                            <strong>📊 Informações:</strong><br>
                            • Bot: {self.bot.user.name if self.bot and self.bot.user else 'Conectando...'}<br>
                            • Servidores: {len(self.bot.guilds) if self.bot and self.bot.guilds else 0}<br>
                            • Voz: {'✅ Conectado' if self.bot and self.bot.voz_conectada else '❌ Desconectado'}<br>
                            • Ping: {round(self.bot.latency * 1000) if self.bot and self.bot.latency else 0}ms
                        </div>
                        <div class="commands">
                            <strong>🎮 Comandos do Bot:</strong><br>
                            <code>!help</code> - Lista todos os comandos<br>
                            <code>!ping</code> - Verifica latência<br>
                            <code>!status</code> - Status do bot<br>
                            <code>!info</code> - Informações<br>
                            <code>!cargos</code> - Lista cargos<br>
                            <code>!entrar</code> - Entra na call WaveX<br>
                            <code>!sair</code> - Sai da call<br>
                            <code>!call</code> - Status da call
                        </div>
                        <footer>
                            Desenvolvido para comunidade WaveX | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
                        </footer>
                    </div>
                </body>
                </html>
                """
                return web.Response(text=html, content_type='text/html')
            
            async def handle_api(request):
                return web.json_response({
                    "status": "online",
                    "timestamp": datetime.now().isoformat(),
                    "bot": {
                        "nome": self.bot.user.name if self.bot and self.bot.user else None,
                        "id": self.bot.user.id if self.bot and self.bot.user else None,
                        "ping": round(self.bot.latency * 1000) if self.bot and self.bot.latency else 0
                    },
                    "servidores": len(self.bot.guilds) if self.bot and self.bot.guilds else 0,
                    "voz_conectada": self.bot.voz_conectada if self.bot else False
                })
            
            async def handle_health(request):
                return web.json_response({
                    "status": "healthy",
                    "timestamp": datetime.now().isoformat()
                })
            
            self.app.router.add_get('/', handle_home)
            self.app.router.add_get('/api', handle_api)
            self.app.router.add_get('/health', handle_health)
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # Usar porta do Render (10000)
            port = int(os.environ.get('PORT', 10000))
            self.site = web.TCPSite(self.runner, '0.0.0.0', port)
            await self.site.start()
            
            print(f"🌐 Site público rodando na porta {port}")
            
        except Exception as e:
            print(f"⚠️ Erro ao iniciar servidor: {e}")
    
    async def stop(self):
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()
    
    def set_bot(self, bot):
        self.bot = bot

# Criar a instância do keep_alive (ESTA LINHA ESTAVA FALTANDO!)
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
              "`!info` - Informações do bot\n"
              "`!voz_estado` - Diagnóstico da voz",
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

@bot.command(name="voz_estado")
async def voz_estado(ctx):
    """!voz_estado - Diagnóstico completo da voz"""
    
    embed = discord.Embed(
        title="🔊 Diagnóstico de Voz",
        color=discord.Color.blue()
    )
    
    # Limpar conexões fantasmas primeiro
    for voz in bot.voice_clients:
        if not voz.is_connected():
            embed.add_field(name="⚠️ Conexão Fantasma", value=f"Canal {voz.channel.name} foi removido", inline=False)
            await voz.disconnect(force=True)
    
    # Status atual
    if ctx.voice_client and ctx.voice_client.is_connected():
        embed.add_field(
            name="✅ Status Atual",
            value=f"Conectado em: {ctx.voice_client.channel.mention}\nServidor: {ctx.guild.name}",
            inline=False
        )
    else:
        embed.add_field(name="❌ Status Atual", value="Desconectado", inline=False)
    
    # Conexões do bot
    if bot.voice_clients:
        for i, voz in enumerate(bot.voice_clients, 1):
            status = "✅ Conectado" if voz.is_connected() else "❌ Desconectado (fantasma)"
            embed.add_field(
                name=f"Conexão {i}",
                value=f"{status}\nCanal: {voz.channel.name if voz.channel else 'Nenhum'}\nServidor: {voz.guild.name}",
                inline=False
            )
    else:
        embed.add_field(name="📋 Conexões", value="Nenhuma conexão ativa", inline=False)
    
    # Canal alvo
    canal = ctx.guild.get_channel(bot.canal_voz_id)
    if canal:
        embed.add_field(
            name="🎯 Canal Alvo",
            value=f"{canal.mention}\nID: {canal.id}",
            inline=False
        )
    else:
        embed.add_field(name="🎯 Canal Alvo", value="❌ Não encontrado!", inline=False)
    
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
    
    # Limpar conexões fantasmas
    for voz in bot.voice_clients:
        if not voz.is_connected():
            try:
                await voz.disconnect(force=True)
            except:
                pass
    
    # Verificar se já está conectado
    if ctx.voice_client and ctx.voice_client.is_connected():
        await ctx.send(f"✅ Já estou conectado em **{ctx.voice_client.channel.name}**!")
        return
    
    canal = ctx.guild.get_channel(bot.canal_voz_id)
    
    if not canal:
        await ctx.send("❌ Canal WaveX não encontrado!")
        return
    
    try:
        await ctx.send(f"🔊 Conectando ao canal **{canal.name}**...")
        
        # Conectar
        await canal.connect()
        bot.voz_conectada = True
        await ctx.send(f"✅ Conectado ao canal **{canal.name}**!")
        
    except discord.errors.ClientException as e:
        error_msg = str(e)
        if "Already connected" in error_msg:
            await ctx.send("✅ Já estou conectado em algum canal!")
            bot.voz_conectada = True
        else:
            await ctx.send(f"❌ Erro: {error_msg}")
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@bot.command(name="sair")
async def sair_call(ctx):
    """!sair - Sai da call"""
    
    if not ctx.voice_client:
        await ctx.send("❌ Não estou em nenhum canal de voz!")
        return
    
    try:
        canal_nome = ctx.voice_client.channel.name
        await ctx.voice_client.disconnect()
        bot.voz_conectada = False
        await ctx.send(f"✅ Desconectado de **{canal_nome}**!")
    except Exception as e:
        await ctx.send(f"❌ Erro ao desconectar: {e}")

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
    
    # Não conectar automaticamente - apenas comando manual
    print("\n🔊 Para conectar à call, use o comando !entrar")
    
    # Status personalizado
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
        'modules.staff_manager',
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
    
    # Configurar keep-alive com o bot
    keep_alive.set_bot(bot)
    
    # Iniciar keep-alive
    try:
        print("\n🌐 Iniciando servidor keep-alive...")
        await keep_alive.start()
    except Exception as e:
        print(f"⚠️ Erro no keep-alive: {e}")
    
    # Carregar módulos
    await carregar_modulos()
    
    # Conectar ao Discord
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
        await keep_alive.stop()
        await bot.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Até mais!")
