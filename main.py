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
    """Verifica se já existe uma instância do bot rodando"""
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

# ==================== CONFIGURAÇÕES DO BOT ====================
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
        
        self.servidores_sincronizados = set()
        self.comando_uso = {}
        self.voz_conectada = False
        self.canal_voz_alvo = "💜・𝐖𝐚𝐯𝐞𝐗"
    
    async def setup_hook(self):
        """Sincroniza comandos assim que o bot estiver pronto"""
        print("🔄 Configurando bot...")
    
    async def sincronizar_todos_servidores(self):
        """Sincroniza comandos para TODOS os servidores"""
        print("\n" + "="*60)
        print("🔄 SINCRONIZANDO COMANDOS...")
        print("="*60)
        
        total = 0
        for guild in self.guilds:
            try:
                # Limpar comandos antigos
                self.tree.clear_commands(guild=guild)
                
                # Copiar comandos globais para o servidor
                self.tree.copy_global_to(guild=guild)
                
                # Sincronizar
                comandos = await self.tree.sync(guild=guild)
                self.servidores_sincronizados.add(guild.id)
                total += 1
                
                print(f"✅ {guild.name}: {len(comandos)} comandos")
                
            except Exception as e:
                print(f"❌ Erro em {guild.name}: {e}")
        
        print(f"\n📊 Total: {total} servidores sincronizados")
        print("="*60)
        return total
    
    async def conectar_ao_canal_voz(self):
        """Conecta ao canal de voz"""
        print("\n" + "="*60)
        print("🔊 VERIFICANDO CANAL DE VOZ")
        print("="*60)
        
        if not self.guilds:
            print("❌ Bot não está em nenhum servidor")
            return None
        
        for guild in self.guilds:
            print(f"\n📋 Servidor: {guild.name}")
            
            # Listar todos os canais de voz
            canais_voz = guild.voice_channels
            if not canais_voz:
                print("   ❌ Nenhum canal de voz encontrado")
                continue
            
            print(f"   🎤 Canais disponíveis: {len(canais_voz)}")
            
            for channel in canais_voz:
                # Verificar se o nome corresponde (ignorando formatação)
                if self.canal_voz_alvo in channel.name or channel.name in self.canal_voz_alvo:
                    print(f"   ✅ Canal encontrado: {channel.name}")
                    
                    # Verificar permissões
                    permissoes = channel.permissions_for(guild.me)
                    if not permissoes.connect:
                        print(f"      ❌ Sem permissão de CONNECT")
                        continue
                    
                    try:
                        # Desconectar de conexões existentes
                        for voz in self.voice_clients:
                            if voz.guild == guild:
                                await voz.disconnect()
                        
                        # Conectar
                        voz = await channel.connect()
                        self.voz_conectada = True
                        print(f"      ✅ CONECTADO com sucesso!")
                        return voz
                        
                    except Exception as e:
                        print(f"      ❌ Erro: {e}")
                        continue
            
            print(f"   ❌ Canal '{self.canal_voz_alvo}' não encontrado")
        
        print("\n❌ NÃO FOI POSSÍVEL CONECTAR")
        return None

bot = MeuBot()

# ==================== KEEP-ALIVE SERVER ====================
class KeepAliveServer:
    def __init__(self):
        self.app = None
        self.runner = None
    
    async def start(self):
        try:
            self.app = web.Application()
            
            async def handle_home(request):
                return web.Response(
                    text=f"""🤖 Bot Discord Online

📊 Status:
• Bot: {bot.user if bot.user else 'Conectando...'}
• Servidores: {len(bot.guilds)}
• Comandos: {len(bot.tree.get_commands())}
• Voz: {'✅' if bot.voz_conectada else '❌'}""",
                    content_type='text/plain'
                )
            
            self.app.router.add_get('/', handle_home)
            
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

# ==================== COMANDOS DE VOZ ====================

@bot.tree.command(name="voz_conectar", description="🔊 Conecta ao canal de voz")
async def voz_conectar(interaction: discord.Interaction):
    """Comando para conectar manualmente"""
    await interaction.response.defer(ephemeral=True)
    
    voz = await bot.conectar_ao_canal_voz()
    
    if voz:
        await interaction.followup.send(f"✅ Conectado a {voz.channel.name}!", ephemeral=True)
    else:
        await interaction.followup.send("❌ Não foi possível conectar!", ephemeral=True)

@bot.tree.command(name="voz_desconectar", description="🔇 Desconecta do canal de voz")
async def voz_desconectar(interaction: discord.Interaction):
    """Comando para desconectar"""
    
    if not bot.voice_clients:
        await interaction.response.send_message("❌ Não estou conectado!", ephemeral=True)
        return
    
    for voz in bot.voice_clients:
        await voz.disconnect()
    
    bot.voz_conectada = False
    await interaction.response.send_message("✅ Desconectado!", ephemeral=True)

@bot.tree.command(name="voz_status", description="📊 Mostra status da conexão de voz")
async def voz_status(interaction: discord.Interaction):
    """Mostra status da voz"""
    
    embed = discord.Embed(
        title="🔊 Status da Voz",
        color=discord.Color.blue()
    )
    
    # Status da conexão
    if bot.voice_clients:
        for voz in bot.voice_clients:
            embed.add_field(
                name="✅ Conectado",
                value=f"Canal: {voz.channel.mention}\nServidor: {voz.guild.name}",
                inline=False
            )
    else:
        embed.add_field(name="❌ Desconectado", value="Não estou em nenhum canal", inline=False)
    
    # Canal alvo
    embed.add_field(name="🎯 Canal Alvo", value=f"`{bot.canal_voz_alvo}`", inline=False)
    
    # Canais disponíveis
    canais = interaction.guild.voice_channels
    if canais:
        lista = []
        for c in canais[:5]:
            permissoes = "✅" if c.permissions_for(interaction.guild.me).connect else "❌"
            lista.append(f"{permissoes} {c.name}")
        
        embed.add_field(
            name=f"📋 Canais ({len(canais)})",
            value="\n".join(lista),
            inline=False
        )
    
    await interaction.response.send_message(embed=embed)

# ==================== COMANDOS PRINCIPAIS ====================

@bot.tree.command(name="help", description="📖 Mostra todos os comandos")
async def help_command(interaction: discord.Interaction):
    """Comando de ajuda"""
    
    embed = discord.Embed(
        title=f"🤖 Comandos do {bot.user.name}",
        description="Lista de todos os comandos:",
        color=discord.Color.purple()
    )
    
    # Agrupar comandos
    categorias = {
        "📌 Gerais": [],
        "🎮 Sets": [],
        "🎫 Tickets": [],
        "📋 Cargos": [],
        "🔊 Voz": [],
        "⚙️ Admin": []
    }
    
    for cmd in bot.tree.get_commands():
        if cmd.name in ["help", "ping", "status", "info"]:
            categorias["📌 Gerais"].append(cmd)
        elif cmd.name in ["sets", "aprovamento", "check_id"]:
            categorias["🎮 Sets"].append(cmd)
        elif cmd.name in ["tickets", "setup_tickets"]:
            categorias["🎫 Tickets"].append(cmd)
        elif cmd.name in ["cargos"]:
            categorias["📋 Cargos"].append(cmd)
        elif cmd.name in ["voz_conectar", "voz_desconectar", "voz_status"]:
            categorias["🔊 Voz"].append(cmd)
        elif cmd.name in ["sync", "modulos"]:
            categorias["⚙️ Admin"].append(cmd)
    
    for categoria, comandos in categorias.items():
        if comandos:
            lista = [f"`/{cmd.name}` - {cmd.description}" for cmd in comandos]
            embed.add_field(name=categoria, value="\n".join(lista), inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="🏓 Verifica a latência")
async def ping_command(interaction: discord.Interaction):
    """Comando ping"""
    latency = round(bot.latency * 1000)
    await interaction.response.send_message(f"🏓 Pong! `{latency}ms`")

@bot.tree.command(name="status", description="📊 Status do bot")
async def status_command(interaction: discord.Interaction):
    """Comando status"""
    
    embed = discord.Embed(
        title="📊 Status do Bot",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🤖 Nome", value=bot.user.name, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="📋 Comandos", value=len(bot.tree.get_commands()), inline=True)
    embed.add_field(name="🔊 Voz", value="✅" if bot.voz_conectada else "❌", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info", description="ℹ️ Informações do bot")
async def info_command(interaction: discord.Interaction):
    """Comando info"""
    
    embed = discord.Embed(
        title="ℹ️ Sobre o Bot",
        description="Bot para comunidade Jugadores",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="📌 Versão", value="2.0.0", inline=True)
    embed.add_field(name="📚 Biblioteca", value=f"discord.py {discord.__version__}", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sets", description="🎮 Sistema de sets")
async def sets_command(interaction: discord.Interaction):
    """Comando sets"""
    await interaction.response.send_message("🎮 Sistema de sets (em desenvolvimento)")

@bot.tree.command(name="aprovamento", description="✅ Aprovação de sets")
async def aprovamento_command(interaction: discord.Interaction):
    """Comando aprovamento"""
    await interaction.response.send_message("✅ Aprovação de sets (em desenvolvimento)")

@bot.tree.command(name="check_id", description="🔍 Verifica ID do FiveM")
async def check_id_command(interaction: discord.Interaction):
    """Comando check_id"""
    await interaction.response.send_message("🔍 Verificação de ID (em desenvolvimento)")

@bot.tree.command(name="tickets", description="🎫 Sistema de tickets")
async def tickets_command(interaction: discord.Interaction):
    """Comando tickets"""
    await interaction.response.send_message("🎫 Sistema de tickets (em desenvolvimento)")

@bot.tree.command(name="setup_tickets", description="⚙️ Configura tickets")
@app_commands.default_permissions(administrator=True)
async def setup_tickets_command(interaction: discord.Interaction):
    """Comando setup_tickets"""
    await interaction.response.send_message("⚙️ Configuração de tickets (em desenvolvimento)")

@bot.tree.command(name="cargos", description="📋 Lista todos os cargos")
async def cargos_command(interaction: discord.Interaction):
    """Comando cargos"""
    
    cargos = [role for role in interaction.guild.roles if role.name != "@everyone"]
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
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sync", description="🔄 Sincroniza comandos (admin)")
@app_commands.default_permissions(administrator=True)
async def sync_command(interaction: discord.Interaction):
    """Comando para sincronizar manualmente"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        # Limpar comandos antigos
        bot.tree.clear_commands(guild=interaction.guild)
        
        # Copiar comandos globais
        bot.tree.copy_global_to(guild=interaction.guild)
        
        # Sincronizar
        comandos = await bot.tree.sync(guild=interaction.guild)
        
        await interaction.followup.send(
            f"✅ Sincronizado! {len(comandos)} comandos disponíveis.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

@bot.tree.command(name="modulos", description="📦 Lista módulos carregados")
async def modulos_command(interaction: discord.Interaction):
    """Lista módulos carregados"""
    
    embed = discord.Embed(
        title="📦 Módulos Carregados",
        color=discord.Color.blue()
    )
    
    cogs = list(bot.cogs.keys())
    if cogs:
        embed.add_field(
            name="✅ Ativos",
            value="\n".join([f"• {cog}" for cog in cogs]),
            inline=False
        )
    else:
        embed.add_field(name="ℹ️", value="Nenhum módulo externo carregado", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

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
    print(f"📋 Comandos: {len(bot.tree.get_commands())}")
    print("="*60)
    
    # Listar servidores
    print("\n📋 Servidores:")
    for guild in bot.guilds:
        print(f"   • {guild.name} - {guild.member_count} membros")
    
    # Sincronizar comandos
    await bot.sincronizar_todos_servidores()
    
    # Conectar à voz
    print("\n🔊 Verificando canal de voz...")
    await asyncio.sleep(2)
    await bot.conectar_ao_canal_voz()
    
    # Status
    status = f"/help | {len(bot.guilds)} servers"
    if bot.voz_conectada:
        status += " | 🔊"
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=status
        )
    )
    
    print("\n" + "="*60)
    print("🚀 BOT PRONTO!")
    print("="*60)

@bot.event
async def on_guild_join(guild):
    """Quando entra em um servidor"""
    print(f"\n📥 Entrou em: {guild.name}")
    
    # Sincronizar comandos
    try:
        bot.tree.clear_commands(guild=guild)
        bot.tree.copy_global_to(guild=guild)
        await bot.tree.sync(guild=guild)
        print(f"   ✅ Comandos sincronizados")
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    # Tentar conectar à voz
    if not bot.voz_conectada:
        await bot.conectar_ao_canal_voz()
    
    # Mensagem de boas-vindas
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description="Digite **/** para ver todos os comandos!",
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
            
            # Tentar reconectar
            await asyncio.sleep(5)
            if not bot.voz_conectada:
                await bot.conectar_ao_canal_voz()

# ==================== TRATAMENTO DE ERROS ====================
@bot.tree.error
async def on_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Trata erros"""
    
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Sem permissão!", ephemeral=True)
    else:
        print(f"❌ Erro: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Erro: {error}", ephemeral=True)

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
    
    # Keep-alive
    try:
        await keep_alive.start()
    except:
        pass
    
    # Módulos
    await carregar_modulos()
    
    # Iniciar
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
