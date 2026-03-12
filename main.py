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
intents.voice_states = True  # IMPORTANTE: Necessário para voz

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
        """Conecta ao canal de voz '💜・𝐖𝐚𝐯𝐞𝐗' com debug completo"""
        
        print("\n" + "="*60)
        print("🔊 INICIANDO CONEXÃO DE VOZ - DEBUG")
        print("="*60)
        
        # Verificar se há servidores
        if not self.guilds:
            print("❌ Bot não está em nenhum servidor!")
            return None
        
        print(f"📊 Total de servidores: {len(self.guilds)}")
        
        # Listar todos os servidores
        for i, guild in enumerate(self.guilds, 1):
            print(f"\n📋 Servidor {i}: {guild.name} (ID: {guild.id})")
            print(f"   Membros: {guild.member_count}")
            
            # Listar canais de voz do servidor
            canais_voz = guild.voice_channels
            print(f"   🎤 Canais de voz disponíveis: {len(canais_voz)}")
            
            canal_encontrado = None
            for channel in canais_voz:
                # Verificar se o nome corresponde (ignorando formatação Unicode)
                if self.canal_voz_alvo in channel.name or channel.name in self.canal_voz_alvo:
                    canal_encontrado = channel
                    print(f"   ✅ Canal encontrado: {channel.name}")
                    
                    # Verificar permissões
                    permissoes = channel.permissions_for(guild.me)
                    print(f"      • Permissão de conectar: {permissoes.connect}")
                    print(f"      • Permissão de falar: {permissoes.speak}")
                    print(f"      • Permissão de usar voz: {permissoes.use_voice_activation}")
                    
                    if not permissoes.connect:
                        print(f"      ❌ Sem permissão de CONNECT para {channel.name}")
                        continue
                    
                    try:
                        # Verificar se já está conectado em algum lugar
                        for voz in self.voice_clients:
                            if voz.guild == guild:
                                if voz.channel == channel:
                                    print(f"      ✅ Já conectado em {channel.name}")
                                    self.voz_conectada = True
                                    return voz
                                else:
                                    print(f"      🔄 Desconectando de {voz.channel.name} para conectar no canal correto")
                                    await voz.disconnect()
                        
                        # Conectar ao canal
                        print(f"      🔌 Tentando conectar a {channel.name}...")
                        voz = await channel.connect()
                        self.voz_conectada = True
                        print(f"      ✅ CONECTADO com sucesso a {channel.name}!")
                        return voz
                        
                    except Exception as e:
                        print(f"      ❌ Erro ao conectar: {type(e).__name__} - {e}")
                        traceback.print_exc()
            
            if not canal_encontrado:
                print(f"   ❌ Canal '{self.canal_voz_alvo}' não encontrado neste servidor")
        
        if not self.voz_conectada:
            print("\n❌ NÃO FOI POSSÍVEL CONECTAR EM NENHUM SERVIDOR!")
            print("   Possíveis problemas:")
            print("   1. O canal de voz não existe em nenhum servidor")
            print("   2. O bot não tem permissão de CONNECT no canal")
            print("   3. O bot não está com a intent VOICE_STATES ativada")
            print("   4. O bot não tem permissão de entrar em canais de voz")
        
        print("="*60)
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

# ==================== COMANDOS DE DIAGNÓSTICO DE VOZ ====================

@bot.tree.command(name="voz_debug", description="🔊 Mostra diagnóstico completo da conexão de voz")
async def voz_debug_command(interaction: discord.Interaction):
    """Comando para diagnosticar problemas de voz"""
    
    embed = discord.Embed(
        title="🔊 Diagnóstico de Voz",
        description=f"Servidor: **{interaction.guild.name}**",
        color=discord.Color.blue()
    )
    
    # 1. Verificar intents
    embed.add_field(
        name="📌 Intents",
        value=f"Voice States: {'✅' if bot.intents.voice_states else '❌'}",
        inline=True
    )
    
    # 2. Status da conexão atual
    if bot.voice_clients:
        for voz in bot.voice_clients:
            embed.add_field(
                name="🔊 Conexão Atual",
                value=f"Conectado em: {voz.channel.mention}\nGuild: {voz.guild.name}",
                inline=True
            )
    else:
        embed.add_field(name="🔊 Conexão Atual", value="Desconectado", inline=True)
    
    # 3. Canal alvo
    embed.add_field(
        name="🎯 Canal Alvo",
        value=f"`{bot.canal_voz_alvo}`",
        inline=True
    )
    
    # 4. Listar todos os canais de voz do servidor
    canais_voz = interaction.guild.voice_channels
    if canais_voz:
        lista_canais = []
        for channel in canais_voz:
            permissoes = channel.permissions_for(interaction.guild.me)
            connect = "✅" if permissoes.connect else "❌"
            speak = "✅" if permissoes.speak else "❌"
            
            # Destacar o canal alvo
            if bot.canal_voz_alvo in channel.name or channel.name in bot.canal_voz_alvo:
                lista_canais.append(f"🔹 **{channel.name}** (ID: {channel.id})\n   Conectar: {connect} | Falar: {speak}")
            else:
                lista_canais.append(f"• {channel.name} (ID: {channel.id})\n  Conectar: {connect} | Falar: {speak}")
        
        embed.add_field(
            name=f"📋 Canais de Voz ({len(canais_voz)})",
            value="\n".join(lista_canais[:10]),
            inline=False
        )
    else:
        embed.add_field(name="📋 Canais de Voz", value="Nenhum canal de voz encontrado!", inline=False)
    
    # 5. Permissões do bot
    permissoes_gerais = interaction.guild.me.guild_permissions
    embed.add_field(
        name="🔐 Permissões do Bot",
        value=f"Conectar: {'✅' if permissoes_gerais.connect else '❌'}\n"
              f"Falar: {'✅' if permissoes_gerais.speak else '❌'}\n"
              f"Usar Voz: {'✅' if permissoes_gerais.use_voice_activation else '❌'}",
        inline=True
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="voz_conectar", description="🔊 Conecta ao canal de voz '💜・𝐖𝐚𝐯𝐞𝐗'")
@app_commands.default_permissions(administrator=True)
async def voz_conectar_command(interaction: discord.Interaction):
    """Comando para conectar manualmente ao canal de voz"""
    await interaction.response.defer(ephemeral=True)
    
    voz = await bot.conectar_ao_canal_voz()
    
    if voz:
        await interaction.followup.send(f"✅ Conectado ao canal de voz **{voz.channel.name}**!", ephemeral=True)
    else:
        await interaction.followup.send("❌ Não foi possível conectar ao canal de voz! Use `/voz_debug` para diagnosticar.", ephemeral=True)

@bot.tree.command(name="voz_desconectar", description="🔇 Desconecta do canal de voz")
@app_commands.default_permissions(administrator=True)
async def voz_desconectar_command(interaction: discord.Interaction):
    """Comando para desconectar do canal de voz"""
    
    if not bot.voice_clients:
        await interaction.response.send_message("❌ Bot não está conectado a nenhum canal de voz!", ephemeral=True)
        return
    
    for voz in bot.voice_clients:
        guild_name = voz.guild.name
        channel_name = voz.channel.name
        await voz.disconnect()
    
    bot.voz_conectada = False
    await interaction.response.send_message(f"✅ Desconectado de **{channel_name}** em **{guild_name}**!", ephemeral=True)

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
        "Voz": [],
        "Admin": []
    }
    
    for cmd in bot.tree.get_commands(guild=interaction.guild):
        if cmd.name in ["help", "ping", "status", "info", "servidores"]:
            categorias["Gerais"].append(cmd)
        elif cmd.name in ["sets", "aprovamento", "check_id", "sets_pendentes"]:
            categorias["Sets"].append(cmd)
        elif cmd.name in ["tickets", "setup_tickets", "verificar_acesso"]:
            categorias["Tickets"].append(cmd)
        elif cmd.name in ["cargos"]:
            categorias["Cargos"].append(cmd)
        elif cmd.name in ["painel_rec", "rec_stats", "rec_reset"]:
            categorias["Recrutadores"].append(cmd)
        elif cmd.name in ["premio", "premios"]:
            categorias["Prêmios"].append(cmd)
        elif cmd.name in ["voz_debug", "voz_conectar", "voz_desconectar"]:
            categorias["Voz"].append(cmd)
        elif cmd.name in ["sync", "debug", "comandos_stats", "modulos"]:
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

@bot.tree.command(name="modulos", description="📋 Lista todos os módulos carregados")
async def modulos_command(interaction: discord.Interaction):
    """Comando para ver quais módulos estão carregados"""
    
    embed = discord.Embed(
        title="📦 Módulos Carregados",
        color=discord.Color.blue()
    )
    
    # Listar cogs carregados
    cogs_list = list(bot.cogs.keys())
    if cogs_list:
        embed.add_field(
            name="✅ Cogs Ativos",
            value="\n".join([f"• `{cog}`" for cog in cogs_list]),
            inline=False
        )
    else:
        embed.add_field(name="❌ Cogs", value="Nenhum cog carregado", inline=False)
    
    # Listar comandos disponíveis
    comandos = bot.tree.get_commands()
    embed.add_field(
        name="📋 Comandos Disponíveis",
        value="\n".join([f"• `/{cmd.name}`" for cmd in comandos[:15]]) + 
              (f"\n... e mais {len(comandos)-15}" if len(comandos) > 15 else ""),
        inline=False
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

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

@bot.tree.command(name="cargos", description="📋 Mostra todos os cargos do servidor")
async def cargos_command(interaction: discord.Interaction):
    """Comando /cargos - Vem do módulo cargos_serv"""
    # Este comando será substituído pelo módulo cargos_serv
    await registrar_uso_comando(interaction)
    await interaction.response.send_message("📋 Comando /cargos será carregado pelo módulo cargos_serv!", ephemeral=True)

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
    print(f"🔊 Intent Voz: {'✅ Ativada' if bot.intents.voice_states else '❌ Desativada'}")
    print("="*60)
    
    # Listar servidores com detalhes
    print("\n📋 Servidores conectados:")
    for i, guild in enumerate(bot.guilds, 1):
        print(f"   {i}. {guild.name} (ID: {guild.id}) - {guild.member_count} membros")
        # Mostrar canais de voz
        canais_voz = guild.voice_channels
        if canais_voz:
            print(f"      🎤 Canais de voz: {len(canais_voz)}")
            for channel in canais_voz[:3]:  # Mostrar apenas os primeiros 3
                print(f"         • {channel.name}")
    
    # SINCRONIZAR AUTOMATICAMENTE TODOS OS SERVIDORES
    await bot.sincronizar_todos_servidores()
    
    # CONECTAR AO CANAL DE VOZ
    print("\n" + "="*60)
    print("🔊 INICIANDO CONEXÃO AUTOMÁTICA DE VOZ")
    print("="*60)
    
    # Aguardar um pouco para garantir que tudo está pronto
    await asyncio.sleep(3)
    
    # Tentar conectar
    voz = await bot.conectar_ao_canal_voz()
    
    if voz:
        print(f"\n✅ CONEXÃO DE VOZ ESTABELECIDA COM SUCESSO em {voz.channel.name}!")
    else:
        print("\n❌ FALHA NA CONEXÃO DE VOZ!")
        print("   Use o comando /voz_debug no Discord para diagnosticar.")
    
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
    
    print("\n" + "="*60)
    print("🚀 Bot pronto para receber comandos!")
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
        print("   🔊 Tentando conectar à voz no novo servidor...")
        await asyncio.sleep(1)
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
                    f"• `/voz_debug` - Diagnosticar voz\n"
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
            print(f"🔇 Bot foi desconectado do canal de voz em {before.channel.guild.name}")
            
            # Tentar reconectar após 5 segundos
            await asyncio.sleep(5)
            if not bot.voz_conectada:
                print("🔄 Tentando reconectar ao canal de voz...")
                await bot.conectar_ao_canal_voz()
        elif before.channel != after.channel:
            # Bot foi movido para outro canal
            if after.channel.name == bot.canal_voz_alvo:
                print(f"🔊 Bot movido para {after.channel.name} em {after.channel.guild.name}")
                bot.voz_conectada = True
            else:
                print(f"⚠️ Bot movido para canal diferente: {after.channel.name} em {after.channel.guild.name}")
                bot.voz_conectada = False

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
    ]
    
    carregados = 0
    for modulo in modulos:
        try:
            print(f"🔄 Tentando carregar: {modulo}")
            await bot.load_extension(modulo)
            print(f"   ✅ {modulo} carregado com sucesso!")
            carregados += 1
        except FileNotFoundError:
            print(f"   ❌ {modulo} - Arquivo não encontrado!")
            print(f"      Certifique-se que o arquivo existe em: modules/{modulo.split('.')[-1]}.py")
        except commands.ExtensionAlreadyLoaded:
            print(f"   ⚠️ {modulo} já estava carregado")
            carregados += 1
        except Exception as e:
            print(f"   ❌ Erro ao carregar {modulo}: {type(e).__name__} - {e}")
            traceback.print_exc()
    
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
        print("   - VOICE STATES INTENT")
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
