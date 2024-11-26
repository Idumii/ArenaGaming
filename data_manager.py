import json
import os


class DataManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, summoners_file_path='summoners_to_watch.json', client=None):
        if not hasattr(self, "initialized"):
            self.summoners_file_path = summoners_file_path
            self.summoners_data = {}  # Changed from self.summoners to self.summoners_data
            self.notified_summoners = []
            self.champion_name_dict = self.load_champion_data()
            self.client = client
            self.load_all_summoners()
            if client:
                self.migrate_legacy_data()
            self.initialized = True
            self.notified_games = self.load_notified_games()
            self.notification_channel = None


    def load_all_summoners(self):
        """Load all summoners data from file, preserving existing data"""
        try:
            # Create file if it doesn't exist
            if not os.path.exists(self.summoners_file_path):
                print("Summoners file not found. Creating new file.")
                self.summoners_data = {}
                self.save_summoners_to_watch([], None)
                return self.summoners_data

            # Read existing data
            with open(self.summoners_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    print("Empty summoners file. Initializing with empty structure")
                    self.summoners_data = {}
                else:
                    try:
                        self.summoners_data = json.loads(content)
                        if not isinstance(self.summoners_data, dict):
                            print("Invalid data format found. Converting to proper structure.")
                            self.summoners_data = {}
                        print("Summoners data loaded successfully")
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        self._create_backup()
                        self.summoners_data = {}

            # Ensure all guilds have an entry but preserve existing data
            if hasattr(self, 'client') and self.client:
                for guild in self.client.guilds:
                    guild_id = str(guild.id)
                    if guild_id not in self.summoners_data:
                        self.summoners_data[guild_id] = []
            
            return self.summoners_data
        except Exception as e:
            print(f"Error loading summoners: {e}")
            return {}

    def load_summoners_to_watch(self, guild_id):
        """Load summoners for a specific guild, creating entry if needed"""
        guild_id = str(guild_id)
        if not hasattr(self, 'summoners_data'):
            self.load_all_summoners()
        return self.summoners_data.get(guild_id, [])

    def save_summoners_to_watch(self, summoners, guild_id):
        """Save summoners while preserving existing data"""
        try:
            if guild_id is not None:
                guild_id = str(guild_id)
                if not hasattr(self, 'summoners_data'):
                    self.load_all_summoners()
                self.summoners_data[guild_id] = summoners

            self._create_backup()
            
            with open(self.summoners_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.summoners_data, f, ensure_ascii=False, indent=4)
            
            print(f"Summoners {'for guild ' + guild_id if guild_id else ''} saved successfully")
        except Exception as e:
            print(f"Error saving summoners: {e}")

    def _create_backup(self):
        """Create backup of the summoners file"""
        if os.path.exists(self.summoners_file_path):
            try:
                backup_path = f"{self.summoners_file_path}.backup"
                import shutil
                shutil.copy2(self.summoners_file_path, backup_path)
            except Exception as e:
                print(f"Backup creation failed: {e}")

    def get_summoners_for_guild(self, guild_id):
        """Get summoners for a specific guild"""
        guild_id = str(guild_id)
        return self.summoners_data.get(guild_id, [])            

    def print_summoners_to_watch(self, prefix=''):
        print(f"{prefix} Summoners to watch: {self.summoners}")

    def load_champion_data(self):
        try:
            with open('champion.json', 'r', encoding='utf-8') as f:
                champion_data = json.load(f)
            return {int(info['key']): info['name'] for info in champion_data['data'].values()}
        except Exception as e:
            print(f"Failed to load champion data: {e}")
            return {}

    def get_champion_name(self, champion_id):
        return self.champion_name_dict.get(champion_id, "Unknown Champion")

    def add_notified_summoner(self, puuid, game_id):
        if not any(entry['puuid'] == puuid and entry['game_id'] == game_id for entry in self.notified_summoners):
            self.notified_summoners.append(
                {"puuid": puuid, "game_id": game_id})
        print(f"Added {puuid} to notified_summoners with gameId: {game_id}")
        print(self.notified_summoners)
        return self

    def remove_notified_summoner(self, puuid):
        self.notified_summoners = [
            entry for entry in self.notified_summoners if entry['puuid'] != puuid]
        print(f"Removed {puuid} from notified_summoners")

    def remove_specific_notified_summoner(self, puuid, game_id):
        self.notified_summoners = [entry for entry in self.notified_summoners if not (
            entry['puuid'] == puuid and entry['game_id'] == game_id)]
        print(f"Removed {puuid} with gameId {game_id} from notified_summoners")

    def get_notified_summoners(self):
        return self.notified_summoners

    def load_notified_games(self):
        try:
            with open('notified_games.json', 'r') as file:
                return json.load(file)
        except FileNotFoundError:
            return []

    def save_notified_games(self):
        with open('notified_games.json', 'w') as file:
            json.dump(self.notified_games, file)

    def add_notified_game(self, game_id):
        if game_id not in self.notified_games:
            self.notified_games.append(game_id)
            self.save_notified_games()

    def save_settings(self, settings):
        with open('settings.json', 'w') as f:
            json.dump(settings, f, indent=4)

    def load_settings(self):
        try:
            with open('settings.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            default_settings = {"notification_channel": None}
            self.save_settings(default_settings)
            return default_settings

    def set_notification_channel(self, guild_id, channel_id):
        settings = self.load_settings()
        if 'notification_channels' not in settings:
            settings['notification_channels'] = {}
        settings['notification_channels'][str(guild_id)] = channel_id
        self.save_settings(settings)

    def get_notification_channel(self, guild_id):
        settings = self.load_settings()
        return settings.get('notification_channels', {}).get(str(guild_id))


    def migrate_legacy_data(self):
        try:
            # Try to read the old format
            with open(self.summoners_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip():
                    return
                
                old_data = json.loads(content)
                
                # Check if it's in the old format (list instead of dict)
                if isinstance(old_data, list):
                    print("Detected old data format, performing migration...")
                    
                    # Get all guilds the bot is currently in
                    from discord.ext.commands import Bot
                    import discord
                    
                    # Store the old data temporarily
                    temp_data = old_data
                    
                    # Initialize new structure
                    self.summoners = {}
                    
                    # If there's old data, assign it to the first guild we find
                    # You might want to modify this logic based on your needs
                    if temp_data:
                        first_guild = next(iter(self.client.guilds), None)
                        if first_guild:
                            self.summoners[str(first_guild.id)] = temp_data
                            print(f"Migrated {len(temp_data)} summoners to guild {first_guild.id}")
                    
                    # Save the new structure
                    self.save_summoners_to_watch([], None)
                    print("Migration completed successfully")
                
        except Exception as e:
            print(f"Migration failed: {e}")
