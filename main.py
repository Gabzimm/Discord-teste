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
        # Para Windows
        if sys.platform == "win32":
            import win32event, win32api, winerror
            mutex_name = "Bot_Jugadores_Unico"
            mutex = win32event.CreateMutex(None, False, mutex_name)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                print("❌ ERRO: Já existe uma instância do bot rodando!")
                return False
            return True
        else:
            # Para Linux/Mac
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind('\0bot_jugadores_unico')
            return True
    except Exception as e:
        if sys.platform != "win32" and isinstance(e, socket.error):
            print("❌ ERRO: Já existe uma instância do bot rodando!")
            print("   Execute: pkill -f python")
            return False
        return True

if not verificar_instancia_unica():
    sys.exit(1)

# ==================== CONFIGURAÇÕES DO BOT ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True  # Adicionar intent para voz

class MeuBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=None
        )
        
        # Dicionário para controlar quais servidores já sincronizaram
        self.servidores_sincronizados = set()
        
        # Tracking de uso dos comandos
        self.comando_uso = {}
        
        # Variável para controlar a conexão de voz
        self.voz_conectada = False
        self.canal_voz_alvo = "💜・𝐖𝐚𝐯𝐞𝐗"  # Nome do canal de voz
    
    async def setup_hook(self):
        """NÃO sincroniza automaticamente - espera o on_ready"""
        print("🔄 Aguardando conexão com Discord para sincronizar comandos...")
    
    async def sincronizar_comandos(self, guild):
        """Sincroniza comandos para um servidor específico"""
        
        # Verificar se já sincronizou este servidor
        if guild.id in self.servidores_sincronizados:
            return False
        
        try:
            # Sincronizar comandos APENAS para este servidor
            comandos = await self.tree.sync(guild=guild)
            
            # Marcar como sincronizado
            self.servidores_sincronizados.add(guild.id)
            
            print(f"\n✅ Comandos sincronizados em: {guild.name}")
            print(f"   📋 {len(comandos)} comandos:")
            for cmd in comandos[:5]:
                print(f"      → /{cmd.name}")
            if len(comandos) > 5:
                print(f"      ... e mais {len(comandos)-5} comandos")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao sincronizar {guild.name}: {e}")
            return False
    
    async def sincronizar_todos_servidores(self):
        """Sincroniza comandos para TODOS os servidores que o bot está"""
        
        print("\n" + "="*60)
        print("🔄 SINCRONIZANDO COMANDOS PARA TODOS OS SERVIDORES")
        print("="*60)
        
        total = 0
        for guild in self.guilds:
            if await self.sincronizar_comandos(guild):
                total += 1
        
        print("\n" + "="*60)
        print(f"✅ {total} servidores sincronizados com sucesso!")
        print(f"📊 Total de servidores: {len(self.guilds)}")
        print("="*60)
        
        return total
    
    def registrar_uso_comando(self, comando_nome: str, interaction: discord.Interaction) -> None:
        """Registra uso de comando para estatísticas"""
        guild_id = interaction.guild_id if interaction.guild_id else 0
        
        if guild_id not in self.comando_uso:
            self.comando_uso[guild_id] = {}
        
        if comando_nome not in self.comando_uso[guild_id]:
            self.comando_uso[guild_id][comando_nome] = 0
        
        self.comando_uso[guild_id][comando_nome] += 1
    
    async def conectar_ao_canal_voz(self):
        """Conecta ao canal de voz '💜・𝐖𝐚𝐯𝐞𝐗'"""
        
        print("\n🔊 Procurando canal de voz '💜・𝐖𝐚𝐯𝐞𝐗'...")
        
        for guild in self.guilds:
            # Procurar canal de voz com o nome exato
            for channel in guild.voice_channels:
                if channel.name == self.canal_voz_alvo:
                    try:
                        # Verificar permissões
                        if not channel.permissions_for(guild.me).connect:
                            print(f"❌ Sem permissão para conectar em {guild.name}")
                            continue
                        
                        # Conectar ao canal
                        voz = await channel.connect()
                        self.voz_conectada = True
                        print(f"✅ Conectado ao canal de voz '{channel.name}' em {guild.name}")
                        
                        # Opcional: Tocar um som de conexão
                        # voz.play(discord.FFmpegPCMAudio('som_conexao.mp3'))
                        
                        return voz
                    except Exception as e:
                        print(f"❌ Erro ao conectar em {guild.name}: {e}")
        
        print("⚠️ Canal de voz '💜・𝐖𝐚𝐯𝐞𝐗' não encontrado ou inacessível")
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
                    text=f"""🤖 Bot Discord Online - Jugadores

📊 Status:
• Bot: {bot.user if bot.user else 'Conectando...'}
• Servidores: {len(bot.guilds)}
• Comandos: {len(bot.tree.get_commands()) if bot.tree else 0}
• Sincronizados: {len(bot.servidores_sincronizados)}
• Voz: {'✅ Conectado' if bot.voz_conectada else '❌ Desconectado'}

💡 Digite / no Discord para ver os comandos!""",
                    content_type='text/plain'
                )
            
            async def handle_health(request):
                return web.json_response({
                    "status": "online",
                    "timestamp": datetime.now().isoformat(),
                    "bot": {
                        "nome": str(bot.user) if bot.user else None,
                        "id": bot.user.id if bot.user else None,
                        "latencia": round(bot.latency * 1000) if bot.latency else 0
                    },
                    "servidores": len(bot.guilds),
                    "comandos": len(bot.tree.get_commands()) if bot.tree else 0,
                    "sincronizados": len(bot.servidores_sincronizados),
                    "voz_conectada": bot.voz_conectada
                })
            
            self.app.router.add_get('/', handle_home)
            self.app.router.add_get('/health', handle_health)
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            port = int(os.getenv('PORT', 8080))
            site = web.TCPSite(self.runner, '0.0.0.0', port)
            await site.start()
            
            print(f"🌐 Keep-alive servidor rodando na porta {port}")
            print(f"   Health check: http://localhost:{port}/health")
            
        except Exception as e:
            print(f"⚠️ Erro ao iniciar keep-alive: {e}")
    
    async def stop(self):
        if self.runner:
            await self.runner.cleanup()

keep_alive = KeepAliveServer()

# ==================== FUNÇÃO PARA REGISTRAR USO ====================
async def registrar_uso_comando(interaction: discord.Interaction) -> None:
    """Registra uso de comando"""
    if interaction.command:
        bot.registrar_uso_comando(interaction.command.name, interaction)

# ==================== COMANDOS PRINCIPAIS ====================

@bot.tree.command(name="help", description="📖 Mostra todos os comandos disponíveis")
async def help_command(interaction: discord.Interaction, comando: str = None):
    """Comando /help"""
    await registrar_uso_comando(interaction)
    
    if comando:
        # Ajuda para comando específico
        cmd = None
        for command in bot.tree.get_commands():
            if command.name.lower() == comando.lower():
                cmd = command
                break
        
        if not cmd:
            await interaction.response.send_message(
                f"❌ Comando `{comando}` não encontrado!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📖 Ajuda: /{cmd.name}",
            description=cmd.description or "Sem descrição disponível",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed)
        return
    
    # Menu de ajuda principal
    embed = discord.Embed(
        title=f"🤖 Comandos do {bot.user.name}",
        description="Digite **/** no chat para ver todos os comandos com autocomplete!",
        color=discord.Color.purple()
    )
    
    # Agrupar comandos por categoria
    categorias = {
        "Gerais": [],
        "Sets": [],
        "Tickets": [],
        "Cargos": [],
        "Recrutadores": [],
        "Prêmios": [],
        "Admin": []
    }
    
    for cmd in bot.tree.get_commands(guild=interaction.guild):
        if cmd.name in ["help", "ping", "status", "info", "servidores"]:
            categorias["Gerais"].append(cmd)
        elif cmd.name in ["sets", "aprovamento", "check_id", "sets_pendentes"]:
            categorias["Sets"].append(cmd)
        elif cmd.name in ["tickets", "setup_tickets", "verificar_acesso"]:
            categorias["Tickets"].append(cmd)
        elif cmd.name in ["cargos", "cargos_painel", "fixnick", "cargo_add", "cargo_remove"]:
            categorias["Cargos"].append(cmd)
        elif cmd.name in ["painel_rec", "rec_stats", "rec_reset"]:
            categorias["Recrutadores"].append(cmd)
        elif cmd.name in ["premio", "premios"]:
            categorias["Prêmios"].append(cmd)
        elif cmd.name in ["sync", "reload", "debug", "comandos_stats"]:
            categorias["Admin"].append(cmd)
    
    for categoria, comandos in categorias.items():
        if comandos:
            lista = [f"`/{cmd.name}` - {cmd.description or '...'}" for cmd in sorted(comandos, key=lambda x: x.name)]
            embed.add_field(name=f"📁 **{categoria}**", value="\n".join(lista), inline=False)
    
    embed.set_footer(text=f"Total: {len(bot.tree.get_commands(guild=interaction.guild))} comandos")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="🏓 Verifica a latência do bot")
async def ping_command(interaction: discord.Interaction):
    """Comando /ping"""
    await registrar_uso_comando(interaction)
    
    latency = round(bot.latency * 1000)
    
    if latency < 200:
        cor = discord.Color.green()
        status = "✅ Excelente"
    elif latency < 500:
        cor = discord.Color.orange()
        status = "⚠️ Razoável"
    else:
        cor = discord.Color.red()
        status = "❌ Ruim"
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"**Latência:** {latency}ms\n**Status:** {status}",
        color=cor
    )
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="📊 Mostra status detalhado do bot")
async def status_command(interaction: discord.Interaction):
    """Comando /status"""
    await registrar_uso_comando(interaction)
    
    embed = discord.Embed(
        title="🤖 Status do Bot",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🏷️ Nome", value=bot.user.name, inline=True)
    embed.add_field(name="🆔 ID", value=bot.user.id, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="📊 Comandos", value=len(bot.tree.get_commands()), inline=True)
    embed.add_field(name="🔄 Sincronizados", value=len(bot.servidores_sincronizados), inline=True)
    embed.add_field(name="🔊 Voz", value="✅ Conectado" if bot.voz_conectada else "❌ Desconectado", inline=True)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info", description="ℹ️ Informações sobre o bot")
async def info_command(interaction: discord.Interaction):
    """Comando /info"""
    await registrar_uso_comando(interaction)
    
    embed = discord.Embed(
        title="ℹ️ Sobre o Bot",
        description="Bot desenvolvido para a comunidade Jugadores",
        color=discord.Color.gold()
    )
    
    embed.add_field(name="📌 Versão", value="2.0.0 (Slash Commands)", inline=True)
    embed.add_field(name="📚 Biblioteca", value=f"discord.py {discord.__version__}", inline=True)
    embed.add_field(name="🐍 Python", value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", inline=True)
    
    embed.add_field(
        name="✨ Funcionalidades",
        value="• Sistema de Sets\n"
              "• Sistema de Tickets\n"
              "• Sistema de Cargos\n"
              "• Painel de Recrutadores\n"
              "• Sistema de Prêmios\n"
              "• Cargos do Servidor\n"
              "• Conexão Automática à Voz\n"
              "• E muito mais...",
        inline=False
    )
    
    embed.set_footer(text="Desenvolvido pela comunidade Jugadores • Use /help")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="servidores", description="🏠 Lista os servidores onde o bot está presente")
async def servidores_command(interaction: discord.Interaction):
    """Comando /servidores"""
    await registrar_uso_comando(interaction)
    
    if len(bot.guilds) == 0:
        await interaction.response.send_message("❌ O bot não está em nenhum servidor.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏠 Servidores do Bot",
        description=f"O bot está presente em **{len(bot.guilds)}** servidores:",
        color=discord.Color.purple()
    )
    
    server_list = []
    for i, guild in enumerate(sorted(bot.guilds, key=lambda g: g.member_count, reverse=True)[:10], 1):
        bots = sum(1 for m in guild.members if m.bot)
        humanos = guild.member_count - bots
        
        server_list.append(
            f"**{i}.** {guild.name}\n"
            f"   👥 {guild.member_count} membros ({humanos} humanos, {bots} bots)"
        )
    
    embed.add_field(name="📋 Lista", value="\n".join(server_list), inline=False)
    
    if len(bot.guilds) > 10:
        embed.set_footer(text=f"Mostrando 10 de {len(bot.guilds)} servidores")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="comandos_stats", description="📈 Mostra estatísticas de uso dos comandos")
@app_commands.default_permissions(administrator=True)
async def stats_comandos(interaction: discord.Interaction):
    """Mostra quais comandos são mais usados"""
    await registrar_uso_comando(interaction)
    
    guild_id = interaction.guild_id
    
    if guild_id not in bot.comando_uso or not bot.comando_uso[guild_id]:
        await interaction.response.send_message(
            "📊 Nenhum comando foi usado ainda neste servidor!",
            ephemeral=True
        )
        return
    
    top_comandos = sorted(bot.comando_uso[guild_id].items(), key=lambda x: x[1], reverse=True)[:10]
    
    embed = discord.Embed(
        title="📊 Comandos Mais Usados",
        description=f"No servidor **{interaction.guild.name}**",
        color=discord.Color.gold()
    )
    
    stats = "\n".join([f"**{i}.** `/{cmd}` - {count} uso(s)" 
                      for i, (cmd, count) in enumerate(top_comandos, 1)])
    
    embed.add_field(name="📈 Top 10", value=stats, inline=False)
    
    total_usos = sum(bot.comando_uso[guild_id].values())
    embed.set_footer(text=f"Total de usos: {total_usos}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="sync", description="🔄 Força sincronização dos comandos (admin)")
@app_commands.default_permissions(administrator=True)
async def sync_command(interaction: discord.Interaction):
    """Comando para forçar sincronização manual"""
    await interaction.response.defer(ephemeral=True)
    
    try:
        comandos = await bot.tree.sync(guild=interaction.guild)
        bot.servidores_sincronizados.add(interaction.guild.id)
        
        await interaction.followup.send(
            f"✅ Comandos sincronizados! {len(comandos)} comandos disponíveis.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

@bot.tree.command(name="debug", description="🔧 Debug do bot (admin)")
@app_commands.default_permissions(administrator=True)
async def debug_command(interaction: discord.Interaction):
    """Comando de debug"""
    await interaction.response.defer(ephemeral=True)
    
    embed = discord.Embed(
        title="🔧 Debug Info",
        color=discord.Color.blue()
    )
    
    embed.add_field(name="🤖 Bot", value=bot.user.name, inline=True)
    embed.add_field(name="🆔 ID", value=bot.user.id, inline=True)
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="📊 Comandos", value=len(bot.tree.get_commands()), inline=True)
    embed.add_field(name="🔄 Sincronizados", value=len(bot.servidores_sincronizados), inline=True)
    embed.add_field(name="🔊 Voz", value="✅ Conectado" if bot.voz_conectada else "❌ Desconectado", inline=True)
    
    # Comandos neste servidor
    guild_commands = bot.tree.get_commands(guild=interaction.guild)
    embed.add_field(
        name=f"📋 Comandos em {interaction.guild.name}",
        value="\n".join([f"`/{cmd.name}`" for cmd in guild_commands[:10]]) + 
              (f"\n... e mais {len(guild_commands)-10}" if len(guild_commands) > 10 else ""),
        inline=False
    )
    
    await interaction.followup.send(embed=embed, ephemeral=True)

# ==================== COMANDOS DE VOZ ====================

@bot.tree.command(name="voz_conectar", description="🔊 Conecta ao canal de voz '💜・𝐖𝐚𝐯𝐞𝐗'")
@app_commands.default_permissions(administrator=True)
async def voz_conectar_command(interaction: discord.Interaction):
    """Comando para conectar manualmente ao canal de voz"""
    await interaction.response.defer(ephemeral=True)
    
    voz = await bot.conectar_ao_canal_voz()
    
    if voz:
        await interaction.followup.send("✅ Conectado ao canal de voz!", ephemeral=True)
    else:
        await interaction.followup.send("❌ Não foi possível conectar ao canal de voz!", ephemeral=True)

@bot.tree.command(name="voz_desconectar", description="🔇 Desconecta do canal de voz")
@app_commands.default_permissions(administrator=True)
async def voz_desconectar_command(interaction: discord.Interaction):
    """Comando para desconectar do canal de voz"""
    
    if not bot.voice_clients:
        await interaction.response.send_message("❌ Bot não está conectado a nenhum canal de voz!", ephemeral=True)
        return
    
    for voz in bot.voice_clients:
        await voz.disconnect()
    
    bot.voz_conectada = False
    await interaction.response.send_message("✅ Desconectado do canal de voz!", ephemeral=True)

# ==================== COMANDOS EXEMPLO (SETS, TICKETS, ETC) ====================

@bot.tree.command(name="sets", description="🎮 Sistema de sets")
async def sets_command(interaction: discord.Interaction):
    """Comando /sets"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("🎮 Comando /sets executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="aprovamento", description="✅ Sistema de aprovamento de sets")
async def aprovamento_command(interaction: discord.Interaction):
    """Comando /aprovamento"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("✅ Comando /aprovamento executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="check_id", description="🔍 Verifica ID do FiveM")
async def check_id_command(interaction: discord.Interaction):
    """Comando /check_id"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("🔍 Comando /check_id executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="sets_pendentes", description="⏳ Mostra sets pendentes")
async def sets_pendentes_command(interaction: discord.Interaction):
    """Comando /sets_pendentes"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("⏳ Comando /sets_pendentes executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="tickets", description="🎫 Sistema de tickets")
async def tickets_command(interaction: discord.Interaction):
    """Comando /tickets"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("🎫 Comando /tickets executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="setup_tickets", description="⚙️ Configura sistema de tickets")
@app_commands.default_permissions(administrator=True)
async def setup_tickets_command(interaction: discord.Interaction):
    """Comando /setup_tickets"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("⚙️ Comando /setup_tickets executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="verificar_acesso", description="🔐 Verifica acesso a tickets")
async def verificar_acesso_command(interaction: discord.Interaction):
    """Comando /verificar_acesso"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("🔐 Comando /verificar_acesso executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="cargos_painel", description="🎛️ Painel de gerenciamento de cargos")
@app_commands.default_permissions(administrator=True)
async def cargos_painel_command(interaction: discord.Interaction):
    """Comando /cargos_painel"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("🎛️ Comando /cargos_painel executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="fixnick", description="🔄 Corrige o nickname de um usuário")
async def fixnick_command(interaction: discord.Interaction, usuario: discord.Member = None):
    """Comando /fixnick"""
    await registrar_uso_comando(interaction)
    member = usuario or interaction.user
    await interaction.response.send_message(f"🔄 Corrigindo nickname de {member.mention}... (Sistema em desenvolvimento)")

@bot.tree.command(name="cargo_add", description="➕ Adiciona cargo a um usuário")
@app_commands.default_permissions(administrator=True)
async def cargo_add_command(interaction: discord.Interaction):
    """Comando /cargo_add"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("➕ Comando /cargo_add executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="cargo_remove", description="➖ Remove cargo de um usuário")
@app_commands.default_permissions(administrator=True)
async def cargo_remove_command(interaction: discord.Interaction):
    """Comando /cargo_remove"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("➖ Comando /cargo_remove executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="painel_rec", description="👥 Painel de recrutadores")
@app_commands.default_permissions(administrator=True)
async def painel_rec_command(interaction: discord.Interaction):
    """Comando /painel_rec"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("👥 Comando /painel_rec executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="rec_stats", description="📊 Estatísticas de recrutadores")
async def rec_stats_command(interaction: discord.Interaction):
    """Comando /rec_stats"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("📊 Comando /rec_stats executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="rec_reset", description="🔄 Reseta estatísticas de recrutadores")
@app_commands.default_permissions(administrator=True)
async def rec_reset_command(interaction: discord.Interaction):
    """Comando /rec_reset"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("🔄 Comando /rec_reset executado! (Sistema em desenvolvimento)")

@bot.tree.command(name="premio", description="🏆 Dá prêmio para um usuário")
@app_commands.default_permissions(administrator=True)
async def premio_command(interaction: discord.Interaction, usuario: discord.Member, tipo: str = None):
    """Comando /premio"""
    await registrar_uso_comando(interaction)
    tipo_texto = f" do tipo `{tipo}`" if tipo else ""
    await interaction.response.send_message(f"🏆 Dando prêmio{tipo_texto} para {usuario.mention}... (Sistema em desenvolvimento)")

@bot.tree.command(name="premios", description="🏆 Lista os prêmios disponíveis")
async def premios_list_command(interaction: discord.Interaction):
    """Comando /premios"""
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("🏆 Comando /premios executado! (Sistema em desenvolvimento)")

# ==================== EVENTOS ====================
@bot.event
async def on_ready():
    print("\n" + "="*60)
    print("✅ BOT CONECTADO COM SUCESSO!")
    print("="*60)
    print(f"🤖 Nome: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📡 Ping: {round(bot.latency * 1000)}ms")
    print(f"🏠 Servidores: {len(bot.guilds)}")
    print(f"📊 Comandos Carregados: {len(bot.tree.get_commands())}")
    print("="*60)
    
    # Listar servidores
    print("\n📋 Servidores conectados:")
    for i, guild in enumerate(bot.guilds, 1):
        print(f"   {i}. {guild.name} - {guild.member_count} membros")
    
    # SINCRONIZAR AUTOMATICAMENTE TODOS OS SERVIDORES
    await bot.sincronizar_todos_servidores()
    
    # CONECTAR AO CANAL DE VOZ
    print("\n🔊 Tentando conectar ao canal de voz...")
    await bot.conectar_ao_canal_voz()
    
    # Status personalizado
    status_text = f"/help | {len(bot.guilds)} servidores"
    if bot.voz_conectada:
        status_text += " | 🔊 Voz"
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=status_text
        )
    )
    
    print("\n🚀 Bot pronto para receber comandos!")
    print("="*60)

@bot.event
async def on_guild_join(guild):
    """Quando entra em um NOVO servidor"""
    print(f"\n📥 Entrou em NOVO servidor: {guild.name} (ID: {guild.id})")
    print(f"   Membros: {guild.member_count}")
    
    # Sincronizar comandos para o novo servidor automaticamente
    await bot.sincronizar_comandos(guild)
    
    # Tentar conectar ao canal de voz se ainda não estiver conectado
    if not bot.voz_conectada:
        await bot.conectar_ao_canal_voz()
    
    # Enviar mensagem de boas-vindas
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description=(
                    f"Olá! Sou o **{bot.user.name}** e uso **Slash Commands**!\n\n"
                    f"📝 **Como usar:**\n"
                    f"• Digite **/** no chat para ver todos os comandos\n"
                    f"• Use **/help** para ver a lista completa\n\n"
                    f"✨ **Principais comandos:**\n"
                    f"• `/ping` - Verificar latência\n"
                    f"• `/status` - Status do bot\n"
                    f"• `/cargos` - Listar cargos do servidor\n"
                    f"• `/sets` - Sistema de sets\n"
                    f"• `/tickets` - Sistema de tickets"
                ),
                color=discord.Color.green()
            )
            embed.set_footer(text="Desenvolvido para comunidade Jugadores")
            
            await channel.send(embed=embed)
            break

@bot.event
async def on_guild_remove(guild):
    """Quando sai de um servidor"""
    print(f"📤 Bot saiu do servidor: {guild.name} (ID: {guild.id})")
    
    if guild.id in bot.servidores_sincronizados:
        bot.servidores_sincronizados.remove(guild.id)
    
    # Se não houver mais servidores, desconectar da voz
    if len(bot.guilds) == 0 and bot.voz_conectada:
        for voz in bot.voice_clients:
            await voz.disconnect()
        bot.voz_conectada = False
        print("🔇 Desconectado da voz (sem servidores)")

@bot.event
async def on_voice_state_update(member, before, after):
    """Monitora mudanças no estado de voz"""
    if member == bot.user:
        if after.channel is None:
            # Bot foi desconectado
            bot.voz_conectada = False
            print("🔇 Bot foi desconectado do canal de voz")
            
            # Tentar reconectar após 5 segundos
            await asyncio.sleep(5)
            if not bot.voz_conectada:
                print("🔄 Tentando reconectar ao canal de voz...")
                await bot.conectar_ao_canal_voz()
        elif before.channel != after.channel:
            # Bot foi movido para outro canal
            if after.channel.name == bot.canal_voz_alvo:
                print(f"🔊 Bot movido para {after.channel.name}")
            else:
                print(f"⚠️ Bot movido para canal diferente: {after.channel.name}")

# ==================== TRATAMENTO DE ERROS ====================
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Tratamento global de erros para slash commands"""
    
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"⏰ Comando em cooldown! Tente novamente em {error.retry_after:.1f}s.",
            ephemeral=True
        )
    
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Você não tem permissão para usar este comando.",
            ephemeral=True
        )
    
    elif isinstance(error, app_commands.BotMissingPermissions):
        await interaction.response.send_message(
            "❌ Eu não tenho permissão para executar este comando.",
            ephemeral=True
        )
    
    elif isinstance(error, app_commands.TransformerError):
        await interaction.response.send_message(
            f"❌ Valor inválido: {error}",
            ephemeral=True
        )
    
    else:
        print(f"❌ Erro em comando: {error}")
        traceback.print_exc()
        
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ Erro: {error}",
                ephemeral=True
            )

# ==================== CARREGAR MÓDULOS ====================
async def carregar_modulos():
    """Carrega todos os módulos do bot"""
    print("\n" + "="*60)
    print("📦 CARREGANDO MÓDULOS")
    print("="*60)
    
    # Lista de módulos para carregar
    modulos = [
        'modules.cargos_serv',     # Sistema de listagem de cargos do servidor
        # Outros módulos serão adicionados quando estiverem prontos
    ]
    
    carregados = 0
    for modulo in modulos:
        try:
            await bot.load_extension(modulo)
            print(f"   ✅ {modulo}")
            carregados += 1
        except Exception as e:
            print(f"   ❌ {modulo}: {e}")
    
    print("\n" + "="*60)
    print(f"📊 TOTAL: {carregados}/{len(modulos)} módulos carregados")
    print("="*60)
    
    return carregados

# ==================== FUNÇÃO PRINCIPAL ====================
async def main():
    print("\n" + "="*60)
    print("🚀 INICIANDO BOT DISCORD - JUGADORES")
    print("="*60)
    
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("\n❌ DISCORD_TOKEN não encontrado!")
        print("\n📌 Configure a variável de ambiente DISCORD_TOKEN")
        sys.exit(1)
    
    # Iniciar keep-alive
    try:
        print("\n🌐 Iniciando servidor keep-alive...")
        await keep_alive.start()
    except Exception as e:
        print(f"⚠️ Erro no keep-alive: {e}")
    
    # Carregar módulos
    await carregar_modulos()
    
    # Conectar ao Discord
    print("\n🔗 Conectando ao Discord...")
    
    try:
        async with bot:
            await bot.start(TOKEN)
    except discord.LoginFailure:
        print("\n❌ ERRO: Token inválido!")
        sys.exit(1)
    except discord.PrivilegedIntentsRequired:
        print("\n❌ ERRO: Intents privilegiadas não habilitadas!")
        print("   Ative no Discord Developer Portal:")
        print("   - SERVER MEMBERS INTENT")
        print("   - MESSAGE CONTENT INTENT")
        print("   - VOICE STATES INTENT (já ativado)")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Bot encerrado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        traceback.print_exc()
    finally:
        print("\n🧹 Limpando recursos...")
        
        # Desconectar da voz antes de fechar
        for voz in bot.voice_clients:
            await voz.disconnect()
        
        await keep_alive.stop()
        await bot.close()
        print("✅ Recursos liberados. Até mais!")

# ==================== PONTO DE ENTRADA ====================
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Bot encerrado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        traceback.print_exc()
