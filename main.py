import os
import discord
from discord import app_commands, ui
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
INIT_COMMAND_NAME = os.getenv("INIT_COMMAND_NAME", "urchin init editor")

editor_sessions = {}

class CodeEditorView(ui.View):
    def __init__(self, thread_id: int):
        super().__init__(timeout=None)
        self.thread_id = thread_id

    @ui.button(label="Edit / Add Line", style=discord.ButtonStyle.primary, custom_id="edit_line_btn")
    async def edit_line(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditLineModal(self.thread_id))

class EditLineModal(ui.Modal, title="Write/Modify Code"):
    line_num = ui.TextInput(label="Line Number (Leave blank to append)", required=False, placeholder="e.g., 1")
    code_text = ui.TextInput(label="Source Code", style=discord.TextStyle.paragraph, placeholder="print('Hello World!')")

    def __init__(self, thread_id: int):
        super().__init__()
        self.thread_id = thread_id

    async def on_submit(self, interaction: discord.Interaction):
        if self.thread_id not in editor_sessions:
            editor_sessions[self.thread_id] = []
        lines = editor_sessions[self.thread_id]
        new_code = self.code_text.value

        if self.line_num.value:
            try:
                idx = int(self.line_num.value) - 1
                if 0 <= idx < len(lines):
                    lines[idx] = new_code
                else:
                    lines.append(new_code)
            except ValueError:
                lines.append(new_code)
        else:
            lines.append(new_code)

        formatted_code = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines))
        display_content = f"### Active File Workspace\n```py\n{formatted_code if formatted_code else '# Empty File'}\n```"
        await interaction.response.edit_message(content=display_content, view=CodeEditorView(self.thread_id))

class CodeEditorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()

bot = CodeEditorBot()

# This callback function defines the project_name parameter explicitly
async def initialize_editor_callback(interaction: discord.Interaction, project_name: str):
    channel = interaction.channel
    
    if isinstance(channel, discord.DMChannel):
        await interaction.response.send_message(
            "Error: Workspaces must be deployed inside a server channel, thread, or forum hub.", 
            ephemeral=True
        )
        return

    if isinstance(channel, discord.Thread):
        await interaction.response.send_message(
            f"Initializing workspace inside this existing thread for {project_name}...", 
            ephemeral=True
        )
        target_thread = channel
    else:
        await interaction.response.send_message(
            f"Spawning private environment for {project_name}...", 
            ephemeral=True
        )
        try:
            target_thread = await channel.create_thread(
                name=f"edit-{project_name}",
                type=discord.ChannelType.private_thread,
                invitable=False
            )
            await target_thread.add_user(interaction.user)
        except Exception as e:
            await interaction.followup.send(
                f"Failed to create private thread: {str(e)}", 
                ephemeral=True
            )
            return

    editor_sessions[target_thread.id] = ["# Welcome to your private code sheet"]
    initial_render = f"### Active File Workspace: {project_name}\n```py\n1: # Welcome to your private code sheet\n```"
    await target_thread.send(content=initial_render, view=CodeEditorView(target_thread.id))

parts = [p.strip().lower() for p in INIT_COMMAND_NAME.split(" ") if p.strip()]

if len(parts) == 3:
    base_name, group_name, cmd_name = parts
    base_group = app_commands.Group(name=base_name, description=f"{base_name} root commands")
    sub_group = app_commands.Group(name=group_name, description=f"{group_name} actions")
    
    actual_command = app_commands.Command(
        name=cmd_name,
        description="Deploy a private workspace thread to isolate code creation",
        callback=initialize_editor_callback
    )
    
    sub_group.add_command(actual_command)
    base_group.add_command(sub_group)
    bot.tree.add_command(base_group)

elif len(parts) == 2:
    base_name, cmd_name = parts
    base_group = app_commands.Group(name=base_name, description=f"{base_name} root commands")
    actual_command = app_commands.Command(
        name=cmd_name,
        description="Deploy a private workspace thread to isolate code creation",
        callback=initialize_editor_callback
    )
    base_group.add_command(actual_command)
    bot.tree.add_command(base_group)

else:
    actual_command = app_commands.Command(
        name=parts[0],
        description="Deploy a private workspace thread to isolate code creation",
        callback=initialize_editor_callback
    )
    bot.tree.add_command(actual_command)

@bot.event
async def on_ready():
    print(f"Bot online as {bot.user}")
    print(f"Spaced layout configured for: /{INIT_COMMAND_NAME}")
    try:
        print("Pushing clean global registration sync...")
        synced = await bot.tree.sync()
        print(f"Global Sync Complete! {len(synced)} root nodes deployed.")
    except Exception as e:
        print(f"Clean Sync Failed: {e}")

if __name__ == "__main__":
    bot.run(BOT_TOKEN)
