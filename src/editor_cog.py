import os
import discord
from discord import app_commands, ui
from discord.ext import commands

# Import the standalone compiler function from our new file
from compiler import execute_source_code

EXTENSION_MAP = {
    "py": "py",
    "js": "js",
    "ts": "ts",
    "cpp": "cpp",
    "c": "c",
    "h": "c",
    "java": "java",
    "cs": "cs",
    "html": "html",
    "css": "css",
    "json": "json",
    "md": "md",
    "rs": "rust",
    "go": "go",
    "sh": "bash"
}

editor_sessions = {}

class CodeEditorView(ui.View):
    def __init__(self, thread_id: int):
        super().__init__(timeout=None)
        self.thread_id = thread_id

    @ui.button(label="Edit / Add Line", style=discord.ButtonStyle.primary, custom_id="edit_line_btn")
    async def edit_line(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(EditLineModal(self.thread_id))

    @ui.button(label="Delete Line", style=discord.ButtonStyle.secondary, custom_id="delete_line_btn")
    async def delete_line(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_modal(DeleteLineModal(self.thread_id))

    @ui.button(label="Clear File Content", style=discord.ButtonStyle.danger, custom_id="delete_file_btn")
    async def delete_file(self, interaction: discord.Interaction, button: ui.Button):
        if self.thread_id in editor_sessions:
            editor_sessions[self.thread_id]["lines"] = []
        await refresh_workspace_display(interaction, self.thread_id)

    @ui.button(label="Remove File From Workspace", style=discord.ButtonStyle.danger, custom_id="remove_file_btn", row=1)
    async def remove_file(self, interaction: discord.Interaction, button: ui.Button):
        if self.thread_id in editor_sessions:
            del editor_sessions[self.thread_id]
        display_content = "### Workspace Closed\nThe file session has been completely removed from memory. Use the initialization command to open a new file."
        await interaction.response.edit_message(content=display_content, view=None)

class EditLineModal(ui.Modal, title="Write / Modify Code"):
    line_num = ui.TextInput(label="Line Number (Leave blank to append)", required=False, placeholder="e.g., 1")
    code_text = ui.TextInput(label="Source Code", style=discord.TextStyle.paragraph, placeholder="Type your code here...")

    def __init__(self, thread_id: int):
        super().__init__()
        self.thread_id = thread_id

    async def on_submit(self, interaction: discord.Interaction):
        if self.thread_id not in editor_sessions:
            editor_sessions[self.thread_id] = {"filename": "untitled.txt", "syntax": "txt", "lines": []}
            
        session = editor_sessions[self.thread_id]
        lines = session["lines"]
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

        await refresh_workspace_display(interaction, self.thread_id)

class DeleteLineModal(ui.Modal, title="Remove Line"):
    line_num = ui.TextInput(label="Line Number to Delete", required=True, placeholder="e.g., 3")

    def __init__(self, thread_id: int):
        super().__init__()
        self.thread_id = thread_id

    async def on_submit(self, interaction: discord.Interaction):
        if self.thread_id in editor_sessions:
            session = editor_sessions[self.thread_id]
            lines = session["lines"]
            try:
                idx = int(self.line_num.value) - 1
                if 0 <= idx < len(lines):
                    lines.pop(idx)
            except ValueError:
                pass
        await refresh_workspace_display(interaction, self.thread_id)

async def refresh_workspace_display(interaction: discord.Interaction, thread_id: int):
    session = editor_sessions.get(thread_id, {"filename": "untitled.txt", "syntax": "txt", "lines": []})
    lines = session["lines"]
    syntax = session["syntax"]
    filename = session["filename"]

    formatted_code = "\n".join(f"{i+1}: {line}" for i, line in enumerate(lines))
    
    display_content = (
        f"### Active File Workspace: `{filename}`\n"
        f"```{syntax}\n"
        f"{formatted_code if formatted_code else '// Empty File'}\n"
        f"```"
    )
    await interaction.response.edit_message(content=display_content, view=CodeEditorView(thread_id))

async def initialize_editor_callback(interaction: discord.Interaction, project_name: str):
    channel = interaction.channel
    
    if isinstance(channel, discord.DMChannel):
        await interaction.response.send_message(
            "Error: Workspaces must be deployed inside a server channel, thread, or forum hub.", 
            ephemeral=True
        )
        return

    filename = project_name.strip()
    suffix = "txt"
    if "." in filename:
        extracted_suffix = filename.split(".")[-1].lower()
        suffix = EXTENSION_MAP.get(extracted_suffix, "txt")

    if isinstance(channel, discord.Thread):
        await interaction.response.send_message(
            f"Initializing file `{filename}` inside this existing thread...", 
            ephemeral=True
        )
        target_thread = channel
    else:
        await interaction.response.send_message(
            f"Spawning private environment for `{filename}`...", 
            ephemeral=True
        )
        try:
            target_thread = await channel.create_thread(
                name=f"edit-{filename}",
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

    welcome_comment = "/* Welcome to your private code sheet */" if suffix in ["js", "ts", "cpp", "c", "java", "cs", "html", "css", "json"] else "# Welcome to your private code sheet"

    editor_sessions[target_thread.id] = {
        "filename": filename,
        "syntax": suffix,
        "lines": [welcome_comment]
    }
    
    initial_render = f"### Active File Workspace: `{filename}`\n```{suffix}\n1: {welcome_comment}\n```"
    await target_thread.send(content=initial_render, view=CodeEditorView(target_thread.id))

async def run_code_callback(interaction: discord.Interaction, file: str):
    thread_id = interaction.channel_id
    session = editor_sessions.get(thread_id)

    if not session or session["filename"].lower() != file.strip().lower():
        await interaction.response.send_message(
            f"Error: No active workspace found matching the file target `{file}` in this thread channel.", 
            ephemeral=True
        )
        return

    # Acknowledge interaction and process background task
    await interaction.response.defer(thinking=True)

    # Call the standalone compiler function
    console_log = await execute_source_code(syntax=session["syntax"], raw_lines=session["lines"])

    response_box = (
        f"### Compilation Console Output for `{file}`\n"
        f"```txt\n"
        f"{console_log}\n"
        f"```"
    )
    await interaction.followup.send(content=response_box)

class EditorCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.register_dynamic_commands()

    def register_dynamic_commands(self):
        cmd_env = os.getenv("INIT_COMMAND_NAME", "urchin init editor")
        parts = [p.strip().lower() for p in cmd_env.split(" ") if p.strip()]

        if len(parts) == 3:
            base_name, group_name, cmd_name = parts
            base_group = app_commands.Group(name=base_name, description=f"{base_name} root commands")
            sub_group = app_commands.Group(name=group_name, description=f"{group_name} actions")
            
            init_cmd = app_commands.Command(name=cmd_name, description="Deploy a private workspace thread to isolate code creation", callback=initialize_editor_callback)
            run_cmd = app_commands.Command(name="run", description="Execute the active target workspace source file", callback=run_code_callback)
            
            sub_group.add_command(init_cmd)
            sub_group.add_command(run_cmd)
            base_group.add_command(sub_group)
            self.bot.tree.add_command(base_group)

        elif len(parts) == 2:
            base_name, cmd_name = parts
            base_group = app_commands.Group(name=base_name, description=f"{base_name} root commands")
            
            init_cmd = app_commands.Command(name=cmd_name, description="Deploy a private workspace thread to isolate code creation", callback=initialize_editor_callback)
            run_cmd = app_commands.Command(name="run", description="Execute the active target workspace source file", callback=run_code_callback)
            
            base_group.add_command(init_cmd)
            base_group.add_command(run_cmd)
            self.bot.tree.add_command(base_group)

        else:
            init_cmd = app_commands.Command(name=parts, description="Deploy a private workspace thread to isolate code creation", callback=initialize_editor_callback)
            self.bot.tree.add_command(init_cmd)

async def setup(bot):
    await bot.add_cog(EditorCog(bot))
