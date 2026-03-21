import discord
from discord.ext import commands, tasks
from discord import ui, ButtonStyle
import asyncio
import json
import os
from typing import Optional, List, Dict

class StaffManagerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.staff_roles = []  # Lista de IDs dos cargos staff
        self.config_file = "staff_config.json"
        self.carregar_config()
        
        print("✅ Sistema de Gerenciamento de Staffs carregado!")
    
    def cog_unload(self):
        """Salva config quando descarregado"""
        self.salvar_config()
    
    def carregar_config(self):
        """Carrega configuração salva"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    self.staff_roles = data.get('staff_roles', [])
                print(f"📂 Configuração carregada: {len(self.staff_roles)} cargos staff")
        except Exception as e:
            print(f"⚠️ Erro ao carregar config: {e}")
            self.staff_roles = []
    
    def salvar_config(self):
        """Salva configuração"""
        try:
            data = {
                'staff_roles': self.staff_roles
            }
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=4)
            print(f"💾 Configuração salva: {len(self.staff_roles)} cargos staff")
        except Exception as e:
            print(f"⚠️ Erro ao salvar config: {e}")
    
    def get_cargos_ordenados(self, guild: discord.Guild) -> List[discord.Role]:
        """Retorna todos os cargos ordenados por posição (do mais alto para o mais baixo)"""
        cargos = [role for role in guild.roles if role.name != "@everyone"]
        cargos.sort(key=lambda r: r.position, reverse=True)
        return cargos
    
    def get_posicao_cargo(self, cargo: discord.Role) -> int:
        """Retorna a posição hierárquica do cargo (1 = mais alto)"""
        cargos = self.get_cargos_ordenados(cargo.guild)
        for i, c in enumerate(cargos, 1):
            if c.id == cargo.id:
                return i
        return 0
    
    def is_staff_role(self, cargo: discord.Role) -> bool:
        """Verifica se um cargo é considerado staff"""
        return cargo.id in self.staff_roles
    
    def is_staff(self, member: discord.Member) -> bool:
        """Verifica se o membro é staff"""
        for role in member.roles:
            if role.id in self.staff_roles:
                return True
        return False
    
    def get_staff_roles(self, guild: discord.Guild) -> List[discord.Role]:
        """Retorna os cargos staff"""
        roles = []
        for role_id in self.staff_roles:
            role = guild.get_role(role_id)
            if role:
                roles.append(role)
        return roles
    
    def get_staff_members(self, guild: discord.Guild) -> List[discord.Member]:
        """Retorna todos os membros staff"""
        staff = []
        for member in guild.members:
            if self.is_staff(member):
                staff.append(member)
        return staff
    
    def get_staff_mentions(self, guild: discord.Guild) -> str:
        """Retorna menção de todos os cargos staff"""
        roles = self.get_staff_roles(guild)
        return " ".join([role.mention for role in roles])
    
    # ===== VIEW DO PAINEL DE CARGOS =====
    
    class StaffRolesView(ui.View):
        def __init__(self, cog, guild):
            super().__init__(timeout=None)
            self.cog = cog
            self.guild = guild
            self.pagina_atual = 0
            self.itens_por_pagina = 10
            self.cargos = cog.get_cargos_ordenados(guild)
            self.total_paginas = (len(self.cargos) + self.itens_por_pagina - 1) // self.itens_por_pagina if self.cargos else 1
            
            self.update_buttons()
        
        def update_buttons(self):
            """Atualiza estado dos botões"""
            # Botões de navegação
            for child in self.children:
                if child.custom_id == "anterior":
                    child.disabled = self.pagina_atual == 0
                elif child.custom_id == "proxima":
                    child.disabled = self.pagina_atual >= self.total_paginas - 1
        
        def get_embed(self) -> discord.Embed:
            """Retorna embed com os cargos da página atual"""
            
            inicio = self.pagina_atual * self.itens_por_pagina
            fim = inicio + self.itens_por_pagina
            cargos_pagina = self.cargos[inicio:fim]
            
            embed = discord.Embed(
                title="👑 Configurar Cargos Staff",
                description=f"**Total: {len(self.cargos)} cargos**\n\n"
                            f"Clique nos botões abaixo para marcar/desmarcar quais cargos são staff.\n"
                            f"✅ = Staff | ⬜ = Não staff\n\n"
                            f"**Cargos (do mais alto para o mais baixo):**",
                color=discord.Color.blue()
            )
            
            for cargo in cargos_pagina:
                posicao = self.cog.get_posicao_cargo(cargo)
                is_staff = self.cog.is_staff_role(cargo)
                status = "✅" if is_staff else "⬜"
                embed.add_field(
                    name=f"{status} `#{posicao}` {cargo.name}",
                    value=f"ID: `{cargo.id}`",
                    inline=False
                )
            
            embed.set_footer(text=f"Página {self.pagina_atual + 1}/{self.total_paginas} • Clique nos botões para configurar")
            
            return embed
        
        @ui.button(label="◀️ Anterior", style=ButtonStyle.blurple, custom_id="anterior")
        async def anterior(self, interaction: discord.Interaction, button: ui.Button):
            self.pagina_atual -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        
        @ui.button(label="Próxima ▶️", style=ButtonStyle.blurple, custom_id="proxima")
        async def proxima(self, interaction: discord.Interaction, button: ui.Button):
            self.pagina_atual += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)
        
        @ui.button(label="✅ Marcar como Staff", style=ButtonStyle.green, custom_id="marcar_staff")
        async def marcar_staff(self, interaction: discord.Interaction, button: ui.Button):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Apenas administradores podem usar este painel!", ephemeral=True)
                return
            
            await interaction.response.send_modal(MarcarStaffModal(self.cog, self))
        
        @ui.button(label="⬜ Desmarcar Staff", style=ButtonStyle.red, custom_id="desmarcar_staff")
        async def desmarcar_staff(self, interaction: discord.Interaction, button: ui.Button):
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Apenas administradores podem usar este painel!", ephemeral=True)
                return
            
            await interaction.response.send_modal(DesmarcarStaffModal(self.cog, self))
        
        @ui.button(label="📋 Listar Staffs", style=ButtonStyle.blurple, custom_id="listar_staffs")
        async def listar_staffs(self, interaction: discord.Interaction, button: ui.Button):
            await interaction.response.defer(ephemeral=True)
            
            staff_members = self.cog.get_staff_members(interaction.guild)
            staff_roles = self.cog.get_staff_roles(interaction.guild)
            
            embed = discord.Embed(
                title="👑 Staffs do Servidor",
                color=discord.Color.blue()
            )
            
            if staff_roles:
                roles_text = "\n".join([f"• {role.mention} (Posição #{self.cog.get_posicao_cargo(role)})" for role in staff_roles])
                embed.add_field(name="📌 Cargos Staff", value=roles_text, inline=False)
            else:
                embed.add_field(name="📌 Cargos Staff", value="Nenhum cargo configurado", inline=False)
            
            if staff_members:
                members_text = "\n".join([f"• {member.mention}" for member in staff_members[:20]])
                if len(staff_members) > 20:
                    members_text += f"\n... e mais {len(staff_members)-20} membros"
                embed.add_field(name="👥 Membros Staff", value=members_text, inline=False)
            else:
                embed.add_field(name="👥 Membros Staff", value="Nenhum membro com cargo staff", inline=False)
            
            embed.set_footer(text=f"Total: {len(staff_members)} membros staff | {len(staff_roles)} cargos staff")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    # ===== MODAIS =====
    
    class CargoSelectView(ui.View):
        def __init__(self, cog, parent_view, action):
            super().__init__(timeout=60)
            self.cog = cog
            self.parent_view = parent_view
            self.action = action
        
        @ui.select(placeholder="Selecione um cargo...", options=[])
        async def cargo_select(self, interaction: discord.Interaction, select: ui.Select):
            cargo_id = int(select.values[0])
            cargo = interaction.guild.get_role(cargo_id)
            
            if not cargo:
                await interaction.response.send_message("❌ Cargo não encontrado!", ephemeral=True)
                return
            
            if self.action == "add":
                if cargo.id not in self.cog.staff_roles:
                    self.cog.staff_roles.append(cargo.id)
                    self.cog.salvar_config()
                    await interaction.response.send_message(f"✅ Cargo {cargo.mention} adicionado como staff!", ephemeral=True)
                else:
                    await interaction.response.send_message(f"⚠️ Cargo {cargo.mention} já é staff!", ephemeral=True)
            else:
                if cargo.id in self.cog.staff_roles:
                    self.cog.staff_roles.remove(cargo.id)
                    self.cog.salvar_config()
                    await interaction.response.send_message(f"✅ Cargo {cargo.mention} removido dos staffs!", ephemeral=True)
                else:
                    await interaction.response.send_message(f"⚠️ Cargo {cargo.mention} não é staff!", ephemeral=True)
            
            # Atualizar o painel principal
            await self.parent_view.edit_original_response(embed=self.parent_view.get_embed(), view=self.parent_view)
        
        async def on_timeout(self):
            for item in self.children:
                item.disabled = True

class MarcarStaffModal(ui.Modal, title="✅ Marcar Cargo como Staff"):
    def __init__(self, cog, parent_view):
        super().__init__()
        self.cog = cog
        self.parent_view = parent_view
    
    cargo_id = ui.TextInput(
        label="ID do cargo:",
        placeholder="Digite o ID do cargo (ex: 123456789)",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            cargo_id = int(self.cargo_id.value)
            cargo = interaction.guild.get_role(cargo_id)
            
            if not cargo:
                await interaction.followup.send(f"❌ Cargo com ID {cargo_id} não encontrado!", ephemeral=True)
                return
            
            if cargo.id in self.cog.staff_roles:
                await interaction.followup.send(f"⚠️ Cargo {cargo.mention} já é staff!", ephemeral=True)
                return
            
            self.cog.staff_roles.append(cargo.id)
            self.cog.salvar_config()
            
            await interaction.followup.send(f"✅ Cargo {cargo.mention} adicionado como staff!", ephemeral=True)
            
            # Atualizar o painel principal
            await self.parent_view.edit_original_response(embed=self.parent_view.get_embed(), view=self.parent_view)
            
        except ValueError:
            await interaction.followup.send("❌ Digite um ID válido!", ephemeral=True)

class DesmarcarStaffModal(ui.Modal, title="⬜ Desmarcar Cargo Staff"):
    def __init__(self, cog, parent_view):
        super().__init__()
        self.cog = cog
        self.parent_view = parent_view
    
    cargo_id = ui.TextInput(
        label="ID do cargo:",
        placeholder="Digite o ID do cargo (ex: 123456789)",
        required=True
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        try:
            cargo_id = int(self.cargo_id.value)
            cargo = interaction.guild.get_role(cargo_id)
            
            if not cargo:
                await interaction.followup.send(f"❌ Cargo com ID {cargo_id} não encontrado!", ephemeral=True)
                return
            
            if cargo.id not in self.cog.staff_roles:
                await interaction.followup.send(f"⚠️ Cargo {cargo.mention} não é staff!", ephemeral=True)
                return
            
            self.cog.staff_roles.remove(cargo.id)
            self.cog.salvar_config()
            
            await interaction.followup.send(f"✅ Cargo {cargo.mention} removido dos staffs!", ephemeral=True)
            
            # Atualizar o painel principal
            await self.parent_view.edit_original_response(embed=self.parent_view.get_embed(), view=self.parent_view)
            
        except ValueError:
            await interaction.followup.send("❌ Digite um ID válido!", ephemeral=True)

# ===== COMANDO PRINCIPAL =====

    @commands.command(name="staffs")
    async def staffs_panel(self, ctx):
        """!staffs - Abre o painel de gerenciamento de staffs"""
        
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ Apenas administradores podem usar este comando!")
            return
        
        view = self.StaffRolesView(self, ctx.guild)
        
        embed = view.get_embed()
        
        await ctx.send(embed=embed, view=view)
    
    # ===== MÉTODOS PARA OUTROS MÓDULOS =====
    
    def is_staff_configured(self, guild: discord.Guild) -> bool:
        """Verifica se há cargos staff configurados"""
        return len(self.get_staff_roles(guild)) > 0
    
    def get_staff_verification_message(self) -> str:
        """Retorna mensagem de erro para sistemas que precisam de staffs configurados"""
        return "❌ **Sistema não configurado!**\n\nUse `!staffs` para configurar os cargos staff antes de usar este sistema."

# ===== SETUP =====
async def setup(bot):
    await bot.add_cog(StaffManagerCog(bot))
    print("✅ Módulo de Gerenciamento de Staffs configurado!")
