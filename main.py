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
            mutex_name = "Bot_Jugadores_Slash_Unico"
            mutex = win32event.CreateMutex(None, False, mutex_name)
            if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
                print("❌ ERRO: Já existe uma instância do bot rodando!")
                return False
            return True
        else:
            # Para Linux/Mac
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.bind('\0bot_jugadores_slash_unico')
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
# Intents necessários para o bot
intents = discord.Intents.default()
intents.members = True      # Para informações de membros
intents.guilds = True       # Para informações de servidores
intents.message_content = False  # Não precisamos para slash commands

class SlashBot(commands.Bot):
    """Classe personalizada do bot com suporte a slash commands"""
    
    def __init__(self):
        super().__init__(
            command_prefix='/',  # Prefixo não será usado, mas é necessário
            intents=intents,
            help_command=None,    # Desabilitar help padrão
            case_insensitive=True
        )
        
    async def setup_hook(self):
        """Executado durante a configuração inicial"""
        print("\n🔄 Configurando slash commands...")
        
        # Carregar todos os módulos (cogs)
        await load_cogs()
        
        # Sincronizar comandos com o Discord
        try:
            print("   Sincronizando comandos globalmente...")
            synced = await self.tree.sync()
            print(f"   ✅ {len(synced)} slash commands sincronizados!")
            
            # Opcional: Para testes mais rápidos, você pode sincronizar com um servidor específico
            # guild = discord.Object(id=SEU_GUILD_ID_AQUI)
            # self.tree.copy_global_to(guild=guild)
            # await self.tree.sync(guild=guild)
            # print(f"   ✅ Comandos sincronizados com servidor de teste!")
            
        except Exception as e:
            print(f"   ❌ Erro ao sincronizar: {e}")

# Instância do bot
bot = SlashBot()

# ==================== KEEP-ALIVE SERVER ====================
class KeepAliveServer:
    """Servidor HTTP para manter o bot online em serviços como Render"""
    
    def __init__(self):
        self.app = None
        self.runner = None
        self.site = None
    
    async def start(self):
        """Inicia o servidor HTTP"""
        try:
            self.app = web.Application()
            
            # Rota principal
            async def handle_home(request):
                return web.Response(
                    text="""🤖 Bot Discord Online - Jugadores (Slash Commands)
                    
Comandos disponíveis via / no Discord
Use /help para ver todos os comandos""",
                    content_type='text/plain'
                )
            
            # Rota de health check
            async def handle_health(request):
                return web.json_response({
                    "status": "online",
                    "timestamp": datetime.now().isoformat(),
                    "bot": {
                        "nome": str(bot.user) if bot.user else "Desconectado",
                        "id": bot.user.id if bot.user else None,
                        "latencia": round(bot.latency * 1000) if bot.latency else 0
                    },
                    "servidores": len(bot.guilds) if bot.guilds else 0,
                    "comandos": len(bot.tree.get_commands()) if bot.tree else 0,
                    "tipo": "Slash Commands Only"
                })
            
            self.app.router.add_get('/', handle_home)
            self.app.router.add_get('/health', handle_health)
            self.app.router.add_get('/stats', handle_health)  # Alias para health
            
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            # Usar porta da variável de ambiente (Render usa PORT)
            port = int(os.getenv('PORT', 8080))
            self.site = web.TCPSite(self.runner, '0.0.0.0', port)
            await self.site.start()
            
            print(f"🌐 Keep-alive servidor rodando na porta {port}")
            print(f"   Health check: http://localhost:{port}/health")
            
        except Exception as e:
            print(f"⚠️ Erro ao iniciar keep-alive: {e}")
    
    async def stop(self):
        """Para o servidor HTTP"""
        if self.site:
            await self.site.stop()
        if self.runner:
            await self.runner.cleanup()

# Instância do servidor keep-alive
keep_alive = KeepAliveServer()

# ==================== SLASH COMMANDS PRINCIPAIS ====================

@bot.tree.command(name="help", description="📖 Mostra a lista de comandos disponíveis")
async def help_command(interaction: discord.Interaction, comando: str = None):
    """
    Comando de ajuda principal
    Uso: /help - Lista todos os comandos
         /help [comando] - Detalhes de um comando específico
    """
    
    if comando:
        # Ajuda para comando específico
        cmd = None
        for command in bot.tree.get_commands():
            if command.name.lower() == comando.lower():
                cmd = command
                break
        
        if not cmd:
            await interaction.response.send_message(
                f"❌ Comando `{comando}` não encontrado! Use `/help` para ver todos os comandos.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📖 Ajuda: /{cmd.name}",
            description=cmd.description or "Sem descrição disponível.",
            color=discord.Color.blue()
        )
        
        # Adicionar informações sobre parâmetros se existirem
        if hasattr(cmd, '_params') and cmd._params:
            params_desc = []
            for param_name, param in cmd._params.items():
                required = "Obrigatório" if param.required else "Opcional"
                params_desc.append(f"• `{param_name}`: {param.description or 'Sem descrição'} ({required})")
            
            if params_desc:
                embed.add_field(
                    name="📝 Parâmetros",
                    value="\n".join(params_desc),
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)
        return
    
    # Menu de ajuda principal
    embed = discord.Embed(
        title=f"🤖 Comandos do {bot.user.name}",
        description="Todos os comandos são acessíveis digitando **/** no chat!",
        color=discord.Color.purple()
    )
    
    # Agrupar comandos por categoria (baseado no nome do módulo)
    categories = {}
    for cmd in bot.tree.get_commands():
        # Determinar categoria
        if cmd.module:
            # Extrair nome do módulo (ex: modules.sets -> Sets)
            module_name = cmd.module.split('.')[-1]
            category = module_name.capitalize()
        else:
            category = "Geral"
        
        if category not in categories:
            categories[category] = []
        categories[category].append(cmd)
    
    # Adicionar comandos ao embed
    for category, commands_list in sorted(categories.items()):
        cmd_list = []
        for cmd in sorted(commands_list, key=lambda x: x.name)[:5]:  # Limitar a 5 por categoria
            cmd_list.append(f"`/{cmd.name}` - {cmd.description or 'Sem descrição'}")
        
        if len(commands_list) > 5:
            cmd_list.append(f"*... e mais {len(commands_list)-5} comandos*")
        
        embed.add_field(
            name=f"📁 **{category}**",
            value="\n".join(cmd_list) if cmd_list else "Nenhum comando",
            inline=False
        )
    
    # Informações adicionais
    embed.add_field(
        name="ℹ️ Informações",
        value=f"📊 **Total de comandos:** {len(bot.tree.get_commands())}\n"
              f"🏠 **Servidores:** {len(bot.guilds)}\n"
              f"📡 **Ping:** {round(bot.latency * 1000)}ms",
        inline=False
    )
    
    embed.set_footer(text="Dica: Digite / no chat para ver todos os comandos disponíveis!")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="ping", description="🏓 Mostra a latência do bot")
async def ping_command(interaction: discord.Interaction):
    """Comando para verificar a latência do bot"""
    
    # Calcular latência
    latency = round(bot.latency * 1000)
    
    # Determinar cor baseada na latência
    if latency < 200:
        color = discord.Color.green()
        status = "✅ Excelente"
    elif latency < 500:
        color = discord.Color.orange()
        status = "⚠️ Razoável"
    else:
        color = discord.Color.red()
        status = "❌ Ruim"
    
    embed = discord.Embed(
        title="🏓 Pong!",
        description=f"**Latência:** {latency}ms",
        color=color
    )
    
    embed.add_field(name="Status da Conexão", value=status, inline=False)
    embed.set_footer(text=f"Solicitado por {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="status", description="📊 Mostra o status detalhado do bot")
async def status_command(interaction: discord.Interaction):
    """Comando para ver status completo do bot"""
    
    embed = discord.Embed(
        title="🤖 Status do Bot",
        description=f"Informações sobre o {bot.user.name}",
        color=discord.Color.blue()
    )
    
    # Informações do bot
    embed.add_field(name="🏷️ Nome", value=bot.user.name, inline=True)
    embed.add_field(name="🆔 ID", value=bot.user.id, inline=True)
    embed.add_field(name="📅 Criado em", value=bot.user.created_at.strftime("%d/%m/%Y"), inline=True)
    
    # Informações de conexão
    embed.add_field(name="📡 Ping", value=f"{round(bot.latency * 1000)}ms", inline=True)
    embed.add_field(name="🏠 Servidores", value=len(bot.guilds), inline=True)
    embed.add_field(name="👥 Usuários", value=sum(g.member_count for g in bot.guilds), inline=True)
    
    # Informações de comandos
    embed.add_field(name="📊 Comandos", value=len(bot.tree.get_commands()), inline=True)
    
    # Módulos carregados
    if bot.cogs:
        modules = ", ".join([cog for cog in bot.cogs.keys()][:5])
        if len(bot.cogs) > 5:
            modules += f" e mais {len(bot.cogs)-5}"
        embed.add_field(name="📦 Módulos", value=modules, inline=False)
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="info", description="ℹ️ Mostra informações sobre o bot")
async def info_command(interaction: discord.Interaction):
    """Comando com informações gerais do bot"""
    
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
              "• Hierarquia Automática\n"
              "• E muito mais...",
        inline=False
    )
    
    embed.set_footer(text="Desenvolvido pela comunidade Jugadores • Use /help")
    
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="servidores", description="🏠 Lista os servidores onde o bot está presente")
async def servidores_command(interaction: discord.Interaction):
    """Comando para listar servidores do bot"""
    
    if len(bot.guilds) == 0:
        await interaction.response.send_message("❌ O bot não está em nenhum servidor.", ephemeral=True)
        return
    
    embed = discord.Embed(
        title="🏠 Servidores do Bot",
        description=f"O bot está presente em **{len(bot.guilds)}** servidores:",
        color=discord.Color.purple()
    )
    
    # Listar servidores (ordenados por número de membros)
    server_list = []
    for i, guild in enumerate(sorted(bot.guilds, key=lambda g: g.member_count, reverse=True)[:10], 1):
        # Contar membros humanos vs bots
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

# ==================== COMANDOS ADMINISTRATIVOS ====================

@bot.tree.command(name="reload", description="🔄 Recarrega todos os módulos (apenas admin)")
@app_commands.default_permissions(administrator=True)
@app_commands.checks.has_permissions(administrator=True)
async def reload_command(interaction: discord.Interaction):
    """Comando para recarregar módulos (apenas admin)"""
    
    await interaction.response.defer(ephemeral=True)
    
    # Lista de módulos para recarregar
    cogs = [
        'modules.sets',
        'modules.tickets',
        'modules.config_cargos',
        'modules.cargos',
        'modules.painel_rec',
        'modules.limpeza',
        'modules.painel_hierarquia',
        'modules.premios',
    ]
    
    results = []
    sucessos = 0
    falhas = 0
    
    for cog in cogs:
        try:
            # Tentar recarregar
            await bot.reload_extension(cog)
            results.append(f"✅ {cog}")
            sucessos += 1
        except commands.ExtensionNotLoaded:
            try:
                # Se não estiver carregado, carregar
                await bot.load_extension(cog)
                results.append(f"✅ {cog} (carregado)")
                sucessos += 1
            except Exception as e:
                results.append(f"❌ {cog} - {str(e)[:50]}")
                falhas += 1
        except Exception as e:
            results.append(f"❌ {cog} - {str(e)[:50]}")
            falhas += 1
    
    # Criar embed com resultados
    embed = discord.Embed(
        title="🔄 Recarregar Módulos",
        description=f"**Resultado:** {sucessos} sucessos, {falhas} falhas",
        color=discord.Color.green() if falhas == 0 else discord.Color.orange()
    )
    
    # Mostrar resultados em páginas se necessário
    result_text = "\n".join(results)
    if len(result_text) > 1024:
        result_text = result_text[:1000] + "..."
    
    embed.add_field(name="📦 Módulos", value=result_text, inline=False)
    
    # Sincronizar comandos novamente
    try:
        await bot.tree.sync()
        embed.add_field(name="🔄 Sincronização", value="✅ Comandos sincronizados", inline=False)
    except Exception as e:
        embed.add_field(name="🔄 Sincronização", value=f"❌ Erro: {e}", inline=False)
    
    await interaction.followup.send(embed=embed)

@reload_command.error
async def reload_error(interaction: discord.Interaction, error):
    """Tratamento de erro para comando reload"""
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Você precisa ser administrador para usar este comando!",
            ephemeral=True
        )

# ==================== EVENTOS DO BOT ====================

@bot.event
async def on_ready():
    """Evento executado quando o bot está pronto"""
    
    print("\n" + "=" * 60)
    print("✅ BOT CONECTADO COM SUCESSO!")
    print("=" * 60)
    print(f"🤖 Nome: {bot.user.name}")
    print(f"🆔 ID: {bot.user.id}")
    print(f"📡 Ping: {round(bot.latency * 1000)}ms")
    print(f"🏠 Servidores: {len(bot.guilds)}")
    print(f"📊 Slash Commands: {len(bot.tree.get_commands())}")
    print("=" * 60)
    
    # Listar comandos disponíveis
    print("\n📋 Slash Commands disponíveis:")
    for cmd in sorted(bot.tree.get_commands(), key=lambda x: x.name):
        print(f"   /{cmd.name} - {cmd.description}")
    
    print("\n🚀 Bot pronto para receber comandos!")
    print("=" * 60)
    
    # Definir status personalizado
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.playing,
            name=f"/help | {len(bot.guilds)} servidores"
        ),
        status=discord.Status.online
    )

@bot.event
async def on_guild_join(guild):
    """Evento quando o bot entra em um novo servidor"""
    print(f"📥 Bot entrou no servidor: {guild.name} (ID: {guild.id})")
    print(f"   Membros: {guild.member_count}")
    
    # Tentar enviar mensagem de boas-vindas
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Obrigado por me adicionar!",
                description=(
                    f"Olá! Sou o **{bot.user.name}** e uso **Slash Commands**!\n\n"
                    f"📝 **Como usar:**\n"
                    f"• Digite **/** no chat para ver todos os comandos\n"
                    f"• Use **/help** para ver a lista completa\n"
                    f"• Os comandos aparecem automaticamente com autocomplete\n\n"
                    f"✨ **Principais comandos:**\n"
                    f"• `/ping` - Verificar latência\n"
                    f"• `/status` - Status do bot\n"
                    f"• `/info` - Informações do bot"
                ),
                color=discord.Color.green()
            )
            embed.set_footer(text="Desenvolvido para comunidade Jugadores")
            
            await channel.send(embed=embed)
            break

@bot.event
async def on_guild_remove(guild):
    """Evento quando o bot sai de um servidor"""
    print(f"📤 Bot saiu do servidor: {guild.name} (ID: {guild.id})")

# ==================== TRATAMENTO DE ERROS ====================

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    """Tratamento global de erros para slash commands"""
    
    # Erros específicos
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
    
    # Erros dos módulos
    elif isinstance(error, app_commands.CommandInvokeError):
        original = error.original
        
        # Log do erro
        print(f"\n❌ Erro em comando:")
        print(f"   Comando: /{interaction.command.name if interaction.command else 'Desconhecido'}")
        print(f"   Usuário: {interaction.user} (ID: {interaction.user.id})")
        print(f"   Servidor: {interaction.guild.name if interaction.guild else 'DM'}")
        print(f"   Erro: {original}")
        print(f"   Traceback: {traceback.format_exc()}")
        
        # Mensagem para o usuário
        if not interaction.response.is_done():
            await interaction.response.send_message(
                "❌ Ocorreu um erro ao executar o comando. Os desenvolvedores foram notificados.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "❌ Ocorreu um erro ao executar o comando.",
                ephemeral=True
            )
    
    # Outros erros
    else:
        print(f"\n❌ Erro não tratado:")
        print(f"   Tipo: {type(error).__name__}")
        print(f"   Erro: {error}")
        
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ Erro: {error}",
                ephemeral=True
            )

# ==================== CARREGAR MÓDULOS ====================

async def load_cogs():
    """Carrega todos os módulos (cogs) do bot"""
    print("\n" + "=" * 60)
    print("🔄 CARREGANDO MÓDULOS...")
    print("=" * 60)
    
    # Lista de módulos para carregar
    cogs = [
        'modules.sets',
        'modules.tickets',
        'modules.config_cargos',
        'modules.cargos',
        'modules.painel_rec',
        'modules.limpeza',
        'modules.painel_hierarquia',
        'modules.premios',
    ]
    
    carregados = 0
    falhas = 0
    
    for cog in cogs:
        print(f"\n🔍 Tentando: {cog}")
        try:
            await bot.load_extension(cog)
            print(f"   ✅ Carregado com sucesso!")
            carregados += 1
        except commands.ExtensionNotFound:
            print(f"   ❌ Módulo não encontrado!")
            falhas += 1
        except commands.NoEntryPointError:
            print(f"   ❌ Não tem função setup!")
            falhas += 1
        except commands.ExtensionAlreadyLoaded:
            print(f"   ⚠️ Já estava carregado!")
            carregados += 1
        except Exception as e:
            print(f"   ❌ Erro: {type(e).__name__}: {e}")
            falhas += 1
    
    print("\n" + "=" * 60)
    print(f"📊 RESUMO: {carregados} módulos carregados, {falhas} falhas")
    print("=" * 60)

# ==================== FUNÇÃO PRINCIPAL ====================

async def main():
    """Função principal do bot"""
    
    print("\n" + "=" * 60)
    print("🚀 INICIANDO BOT COM SLASH COMMANDS")
    print("=" * 60)
    
    # Obter token
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("\n❌ DISCORD_TOKEN não encontrado!")
        print("\n📌 Para configurar:")
        print("   1. No Render: Adicione DISCORD_TOKEN nas Environment Variables")
        print("   2. Local: export DISCORD_TOKEN='seu_token_aqui' (Linux/Mac)")
        print("   3. Local: set DISCORD_TOKEN=seu_token_aqui (Windows)")
        print("\n💡 Obtenha seu token em: https://discord.com/developers/applications")
        sys.exit(1)
    
    # Iniciar servidor keep-alive
    try:
        print("\n🌐 Iniciando servidor keep-alive...")
        await keep_alive.start()
    except Exception as e:
        print(f"⚠️ Erro no keep-alive: {e}")
    
    # Conectar ao Discord
    print("\n🔗 Conectando ao Discord...")
    
    try:
        async with bot:
            await bot.start(TOKEN)
    except discord.LoginFailure:
        print("\n❌ ERRO: Token inválido!")
        print("   Verifique se o DISCORD_TOKEN está correto.")
        sys.exit(1)
    except discord.PrivilegedIntentsRequired:
        print("\n❌ ERRO: Intents privilegiadas não habilitadas!")
        print("   Ative no Discord Developer Portal:")
        print("   - SERVER MEMBERS INTENT")
        print("   - MESSAGE CONTENT INTENT (opcional para slash commands)")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Bot encerrado pelo usuário")
    except Exception as e:
        print(f"\n❌ Erro fatal: {e}")
        traceback.print_exc()
    finally:
        print("\n🧹 Limpando recursos...")
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
