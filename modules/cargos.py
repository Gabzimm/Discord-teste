import discord
from discord.ext import commands
from discord import app_commands, ui, ButtonStyle
import asyncio
from datetime import datetime
import re
from typing import Optional

# ========== CONFIGURAÇÃO SIMPLES ==========
NICKNAME_CONFIG = {
    "👑 | Lider | 00": "00 | {name} | {id}",
    "💎 | Lider | 01": "01 | {name} | {id}",
    "👮 | Lider | 02": "02 | {name} | {id}",
    "🎖️ | Lider | 03": "03 | {name} | {id}",
    "🎖️ | Gerente Geral": "G.Geral | {name} | {id}",
    "🎖️ | Gerente De Farm": "G.Farm | {name} | {id}",
    "🎖️ | Gerente De Pista": "G.Pista | {name} | {id}",
    "🎖️ | Gerente de Recrutamento": "G.Rec | {name} | {id}",
    "🎖️ | Supervisor": "Sup | {name} | {id}",
    "🎖️ | Recrutador": "Rec | {name} | {id}",
    "🎖️ | Ceo Elite": "Ceo E | {name} | {id}",
    "🎖️ | Sub Elite": "Sub E | {name} | {id}",
    "🎖️ | Elite": "E | {name} | {id}",
    "🙅‍♂️ | Membro": "M | {name} | {id}",
}

ORDEM_PRIORIDADE = [
    "👑 | Lider | 00",
    "💎 | Lider | 01",
    "👮 | Lider | 02",
    "🎖️ | Lider | 03",
    "🎖️ | Gerente Geral",
    "🎖️ | Gerente De Farm",
    "🎖️ | Gerente De Pista",
    "🎖️ | Gerente de Recrutamento",
    "🎖️ | Supervisor",
    "🎖️ | Recrutador",
    "🎖️ | Ceo Elite",
    "🎖️ | Sub Elite",
    "🎖️ | Elite",
    "🙅‍♂️ | Membro",
]

# Cargos de staff (quem pode usar o painel)
STAFF_ROLES = [
    "👑 | Lider | 00",
    "💎 | Lider | 01",
    "👮 | Lider | 02",
    "🎖️ | Lider | 03",
    "🎖️ | Gerente Geral",
    "🎖️ | Gerente De Farm",
    "🎖️ | Gerente De Pista",
    "🎖️ | Gerente de Recrutamento",
    "🎖️ | Supervisor",
    "🎖️ | Recrutador",
    "🎖️ | Ceo Elite",
    "🎖️ | Sub Elite",
]

# ========== FUNÇÕES DE NORMALIZAÇÃO ==========
def normalizar_nome(nome: str) -> str:
    """Remove todos os espaços do nome para comparação flexível"""
    if not nome:
        return ""
    return re.sub(r'\s+', '', nome)

def get_cargo_por_nome_flexivel(guild: discord.Guild, nome_busca: str) -> Optional[discord.Role]:
    """Busca cargo ignorando diferenças de espaços no nome"""
    if not nome_busca:
        return None
    
    nome_busca_normalizado = normalizar_nome(nome_busca)
    
    for role in guild.roles:
        nome_role_normalizado = normalizar_nome(role.name)
        if nome_role_normalizado == nome_busca_normalizado:
            return role
    
    return None

def member_tem_cargo_flexivel(member: discord.Member, nome_cargo: str) -> bool:
    """Verifica se o membro tem um cargo ignorando espaços"""
    if not member or not nome_cargo:
        return False
    
    nome_cargo_normalizado = normalizar_nome(nome_cargo)
    
    for role in member.roles:
        nome_role_normalizado = normalizar_nome(role.name)
        if nome_role_normalizado == nome_cargo_normalizado:
            return True
    
    return False

def is_staff(member: discord.Member) -> bool:
    """Verifica se o membro é staff"""
    if member.guild_permissions.administrator:
        return True
    
    for role in member.roles:
        for cargo_staff in STAFF_ROLES:
            if normalizar_nome(role.name) == normalizar_nome(cargo_staff):
                return True
    
    return False

# ========== FUNÇÕES DE NICKNAME ==========
def extrair_parte_nickname(nickname: str) -> str:
    """Extrai a parte do nome do usuário (segunda parte após o primeiro ' | ')"""
    if not nickname:
        return "User"
    
    partes = nickname.split(' | ')
    if len(partes) >= 2:
        return partes[1].strip()
    
    return nickname.strip()

def extrair_id_fivem(nickname: str) -> Optional[str]:
    """Extrai ID do FiveM do nickname (último número após o último ' | ')"""
    if not nickname:
        return None
    
    partes = nickname.split(' | ')
    if len(partes) >= 3:
        ultima_parte = partes[-1].strip()
        if ultima_parte.isdigit():
            return ultima_parte
    
    return None

async def atualizar_nickname(member: discord.Member) -> bool:
    """Atualiza nickname mantendo a estrutura"""
    try:
        if not member.guild.me.guild_permissions.manage_nicknames:
            return False
        
        nickname_atual = member.nick or member.name
        parte_nome = extrair_parte_nickname(nickname_atual)
        id_fivem = extrair_id_fivem(nickname_atual) or "000000"
        
        # Encontrar cargo principal
        cargo_principal = None
        for cargo_nome in ORDEM_PRIORIDADE:
            if member_tem_cargo_flexivel(member, cargo_nome):
                cargo_principal = cargo_nome
                break
        
        if not cargo_principal or cargo_principal not in NICKNAME_CONFIG:
            return False
        
        template = NICKNAME_CONFIG[cargo_principal]
        novo_nick = template.format(name=parte_nome, id=id_fivem)
        
        if len(novo_nick) > 32:
            novo_nick = novo_nick[:32]
        
        if member.nick != novo_nick:
            await member.edit(nick=novo_nick)
            return True
            
    except Exception as e:
        print(f"Erro ao atualizar nickname: {e}")
    
    return False

# ========== SISTEMA DE SELEÇÃO DE CARGO ==========
class CargoSelectView(ui.View):
    """View para selecionar cargo"""
    def __init__(self, member: discord.Member, action: str):
        super().__init__(timeout=60)
        self.member = member
        self.action = action
        
        options = []
        for i, cargo_nome in enumerate(ORDEM_PRIORIDADE):
            if " | " in cargo_nome:
                prefixo = cargo_nome.split(' | ')[0]
            else:
                prefixo = cargo_nome
            
            options.append(
                discord.SelectOption(
                    label=prefixo,
                    description=cargo_nome,
                    value=str(i)
                )
            )
        
        self.select = ui.Select(
            placeholder="Selecione o cargo...",
            options=options,
            custom_id=f"cargo_select_{action}"
        )
        self.select.callback = self.on_select
        self.add_item(self.select)
    
    async def on_select(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        index = int(self.select.values[0])
        cargo_nome = ORDEM_PRIORIDADE[index]
        cargo = get_cargo_por_nome_flexivel(interaction.guild, cargo_nome)
        
        if not cargo:
            await interaction.followup.send("❌ Cargo não encontrado no servidor!", ephemeral=True)
            return
        
        try:
            if self.action == "add":
                await self.member.add_roles(cargo)
                mensagem = f"✅ Cargo `{cargo.name}` adicionado para {self.member.mention}"
            else:
                await self.member.remove_roles(cargo)
                mensagem = f"✅ Cargo `{cargo.name}` removido de {self.member.mention}"
            
            await atualizar_nickname(self.member)
            await interaction.followup.send(mensagem, ephemeral=False)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ Sem permissão!", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

# ========== MODAL DE BUSCA ==========
class CargoModal(ui.Modal, title="🎯 Gerenciar Cargo"):
    """Modal para gerenciar cargo"""
    
    usuario = ui.TextInput(
        label="Usuário (@menção ou ID do FiveM):",
        placeholder="Ex: @João ou 9237",
        required=True
    )
    
    def __init__(self, action: str):
        super().__init__()
        self.action = action
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        if not is_staff(interaction.user):
            await interaction.followup.send("❌ Apenas staff pode usar este comando!", ephemeral=True)
            return
        
        # Buscar usuário
        member = None
        input_text = self.usuario.value
        
        # Se for menção
        if "<@" in input_text:
            user_id = input_text.replace("<@", "").replace(">", "").replace("!", "")
            try:
                member = interaction.guild.get_member(int(user_id))
            except:
                pass
        
        # Se for número (ID FiveM)
        elif input_text.isdigit():
            for guild_member in interaction.guild.members:
                if guild_member.nick and guild_member.nick.endswith(f" | {input_text}"):
                    member = guild_member
                    break
        
        # Se for texto
        else:
            for guild_member in interaction.guild.members:
                if guild_member.nick and input_text.lower() in guild_member.nick.lower():
                    member = guild_member
                    break
                elif input_text.lower() in guild_member.name.lower():
                    member = guild_member
                    break
        
        if not member:
            await interaction.followup.send(f"❌ Usuário `{input_text}` não encontrado!", ephemeral=True)
            return
        
        # Criar embed
        embed = discord.Embed(
            title=f"{'➕ Adicionar' if self.action == 'add' else '➖ Remover'} Cargo",
            description=(
                f"**Usuário:** {member.mention}\n"
                f"**Nickname:** `{member.nick or member.name}`\n"
                f"**ID FiveM:** `{extrair_id_fivem(member.nick) or 'Não encontrado'}`\n\n"
                f"Selecione o cargo abaixo:"
            ),
            color=discord.Color.green() if self.action == 'add' else discord.Color.red()
        )
        
        view = CargoSelectView(member, self.action)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

# ========== VIEW DO PAINEL ==========
class PainelCargosView(ui.View):
    """View principal do painel de cargos"""
    def __init__(self):
        super().__init__(timeout=None)
    
    @ui.button(label="➕ Adicionar Cargo", style=ButtonStyle.green, emoji="➕", custom_id="painel_cargos_add")
    async def add_cargo(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar este painel!", ephemeral=True)
            return
        
        await interaction.response.send_modal(CargoModal("add"))
    
    @ui.button(label="➖ Remover Cargo", style=ButtonStyle.red, emoji="➖", custom_id="painel_cargos_remove")
    async def remove_cargo(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar este painel!", ephemeral=True)
            return
        
        await interaction.response.send_modal(CargoModal("remove"))
    
    @ui.button(label="🔄 Corrigir Nick", style=ButtonStyle.blurple, emoji="🔄", custom_id="painel_cargos_fix")
    async def fix_nick(self, interaction: discord.Interaction, button: ui.Button):
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar este painel!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        success = await atualizar_nickname(interaction.user)
        
        if success:
            await interaction.followup.send(f"✅ Nickname corrigido para `{interaction.user.nick}`", ephemeral=True)
        else:
            await interaction.followup.send("❌ Não foi possível corrigir o nickname", ephemeral=True)

# ========== COG PRINCIPAL ==========
class CargosCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        print("✅ Cog de Cargos carregado!")
    
    # ===== SLASH COMMANDS =====
    
    @app_commands.command(name="cargos_painel", description="🎛️ Mostra o painel de gerenciamento de cargos")
    @app_commands.default_permissions(administrator=True)
    async def cargos_painel(self, interaction: discord.Interaction):
        """Comando /cargos_painel - Cria o painel de cargos"""
        
        embed = discord.Embed(
            title="⚙️ SISTEMA DE CARGOS",
            description=(
                "**Como funciona:**\n"
                "1. Clique em Adicionar ou Remover\n"
                "2. Digite @usuário ou ID do FiveM\n"
                "3. Selecione o cargo\n"
                "✅ Nickname atualiza automaticamente\n\n"
                "**📌 Importante:**\n"
                "• O nickname mantém o nome e ID\n"
                "• Apenas staff pode usar\n\n"
                "**📌 Formato de Nickname:**\n"
                "`Prefixo | Nome | ID`"
            ),
            color=discord.Color.blue()
        )
        
        # Lista de cargos
        cargos_lista = []
        for cargo in ORDEM_PRIORIDADE:
            if " | " in cargo:
                prefixo = cargo.split(' | ')[0]
                nome_completo = cargo
                cargos_lista.append(f"• `{prefixo}` - {nome_completo}")
            else:
                cargos_lista.append(f"• `{cargo}`")
        
        embed.add_field(
            name="📋 Cargos Disponíveis",
            value="\n".join(cargos_lista[:10]) + ("\n..." if len(cargos_lista) > 10 else ""),
            inline=False
        )
        
        embed.add_field(
            name="👑 Staff Autorizado",
            value="\n".join([c.split(' | ')[0] for c in STAFF_ROLES[:8]]),
            inline=False
        )
        
        embed.set_footer(text="Sistema de Cargos • Use os botões abaixo")
        
        view = PainelCargosView()
        await interaction.response.send_message(embed=embed, view=view)
    
    @app_commands.command(name="cargo_add", description="➕ Adiciona um cargo a um usuário")
    async def cargo_add(self, interaction: discord.Interaction, usuario: str):
        """Comando /cargo_add - Atalho para adicionar cargo"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar este comando!", ephemeral=True)
            return
        
        await interaction.response.send_modal(CargoModal("add"))
    
    @app_commands.command(name="cargo_remove", description="➖ Remove um cargo de um usuário")
    async def cargo_remove(self, interaction: discord.Interaction, usuario: str):
        """Comando /cargo_remove - Atalho para remover cargo"""
        if not is_staff(interaction.user):
            await interaction.response.send_message("❌ Apenas staff pode usar este comando!", ephemeral=True)
            return
        
        await interaction.response.send_modal(CargoModal("remove"))
    
    @app_commands.command(name="fixnick", description="🔄 Corrige o nickname de um usuário")
    async def fixnick_slash(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        """Comando /fixnick - Corrige nickname"""
        member = usuario or interaction.user
        
        if member != interaction.user and not is_staff(interaction.user):
            await interaction.response.send_message("❌ Você só pode corrigir seu próprio nickname!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        success = await atualizar_nickname(member)
        
        if success:
            await interaction.followup.send(f"✅ Nickname de {member.mention} corrigido para `{member.nick}`", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Não foi possível corrigir o nickname de {member.mention}", ephemeral=True)
    
    @app_commands.command(name="cargos_lista", description="📋 Mostra a lista de cargos disponíveis")
    async def cargos_lista(self, interaction: discord.Interaction):
        """Comando /cargos_lista - Mostra todos os cargos"""
        
        embed = discord.Embed(
            title="📋 Lista de Cargos",
            description="Hierarquia de cargos do servidor:",
            color=discord.Color.gold()
        )
        
        for i, cargo in enumerate(ORDEM_PRIORIDADE, 1):
            if " | " in cargo:
                prefixo = cargo.split(' | ')[0]
                embed.add_field(
                    name=f"{i}. {prefixo}",
                    value=cargo,
                    inline=True
                )
            else:
                embed.add_field(
                    name=f"{i}. {cargo}",
                    value="‎",
                    inline=True
                )
        
        await interaction.response.send_message(embed=embed)
    
    # ===== EVENTOS =====
    
    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Atualiza nickname quando cargo muda"""
        if before.roles != after.roles:
            await asyncio.sleep(1)
            await atualizar_nickname(after)
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Registra views persistentes"""
        self.bot.add_view(PainelCargosView())
        print("✅ Views do sistema de cargos registradas!")

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(CargosCog(bot))
    print("✅ Sistema de Cargos configurado com slash commands!")
