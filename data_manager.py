import json
import os
from datetime import datetime, timedelta  # Add this import if not already present

class DataManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super().__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self, summoners_file_path='summoners_to_watch.json', client=None):
        if not hasattr(self, "initialized"):
            self.summoners_file_path = summoners_file_path
            self.summoners_data = {}
            self.notified_summoners = []
            self.champion_name_dict = self.load_champion_data()
            self.client = client
            self.lp_tracker = {}  # Add this to track LP for each summoner
            self.temp_lp_data = {}  # Inisialisation de la variable temporaire
            self.lp_data_file = 'lp_data.json'
            self.load_all_summoners()
            if client:
                self.migrate_legacy_data()
            self.initialized = True
            self.notified_games = self.load_notified_games()
            self.notification_channel = None
            

    def store_temp_lp(self, summoner_id, queue_type, lp, tier, rank):
        """Store current LP and rank for a summoner in a specific queue"""
        if summoner_id not in self.lp_tracker:
            self.lp_tracker[summoner_id] = {}
        
        self.lp_tracker[summoner_id][queue_type] = {
            'lp': lp,
            'tier': tier,
            'rank': rank
        }
        print(f"Stored LP data for summoner ID {summoner_id} in {queue_type}")

    def get_lp_difference(self, summoner_id, queue_type, current_lp, current_tier, current_rank):
        """Calculate LP difference between stored and current LP"""
        if summoner_id not in self.lp_tracker or queue_type not in self.lp_tracker[summoner_id]:
            return None

        old_data = self.lp_tracker[summoner_id][queue_type]
        
        # Check for tier/rank changes
        if old_data['tier'] != current_tier or old_data['rank'] != current_rank:
            return f"**{old_data['tier']} {old_data['rank']}** → **{current_tier} {current_rank}**"
        
        # Calculate LP change within same rank
        lp_change = current_lp - old_data['lp']
        if lp_change != 0:
            return f"{'+' if lp_change > 0 else ''}{lp_change} LP"
        
        return None

    # Add this method to DataManager class
    def get_stored_lp(self, summoner_id, queue_type):
        """Get stored LP data for a summoner in a specific queue"""
        if not hasattr(self, 'lp_tracker'):
            return None
        
        if summoner_id not in self.lp_tracker:
            return None
            
        if queue_type not in self.lp_tracker[summoner_id]:
            return None
            
        return self.lp_tracker[summoner_id][queue_type]

    def clear_temp_lp(self, summoner_id):
        """Clear temporary LP data for a summoner"""
        if summoner_id in self.lp_tracker:
            del self.lp_tracker[summoner_id]
            print(f"Cleared LP data for summoner ID {summoner_id}")



    def store_daily_rank(self, summoner_id, ranks_data):
        """Store daily rank data for a summoner"""
        if not hasattr(self, 'daily_ranks'):
            self.load_daily_ranks()
        
        today = datetime.now().strftime('%Y-%m-%d')
        if today not in self.daily_ranks:
            self.daily_ranks[today] = {}
        
        self.daily_ranks[today][summoner_id] = ranks_data
        self.save_daily_ranks()
        print(f"Debug - Stored daily rank for {summoner_id}")

    def load_daily_ranks(self):
        """Load daily ranks from file"""
        try:
            with open('daily_ranks.json', 'r', encoding='utf-8') as f:
                self.daily_ranks = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            self.daily_ranks = {}
        return self.daily_ranks

    def save_daily_ranks(self):
        """Save daily ranks to file"""
        with open('daily_ranks.json', 'w', encoding='utf-8') as f:
            json.dump(self.daily_ranks, f, ensure_ascii=False, indent=4)

    def get_daily_rank_changes(self, summoner_id):
        """Get rank changes since last check"""
        if not hasattr(self, 'daily_ranks'):
            self.load_daily_ranks()
        
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        today_ranks = self.daily_ranks.get(today, {}).get(summoner_id)
        yesterday_ranks = self.daily_ranks.get(yesterday, {}).get(summoner_id)
        
        if not yesterday_ranks:
            return None
        
        changes = []
        if today_ranks:
            for queue_type in ['RANKED_SOLO_5x5', 'RANKED_FLEX_SR']:
                if queue_type in yesterday_ranks and queue_type in today_ranks:
                    old_rank = yesterday_ranks[queue_type]
                    new_rank = today_ranks[queue_type]
                    
                    if (old_rank['tier'] != new_rank['tier'] or 
                        old_rank['rank'] != new_rank['rank'] or 
                        old_rank['lp'] != new_rank['lp']):
                        
                        queue_name = "Solo/Duo" if queue_type == "RANKED_SOLO_5x5" else "Flex"
                        if old_rank['tier'] != new_rank['tier'] or old_rank['rank'] != new_rank['rank']:
                            changes.append({
                                'queue': queue_name,
                                'change_type': 'division',
                                'old': f"{old_rank['tier']} {old_rank['rank']}",
                                'new': f"{new_rank['tier']} {new_rank['rank']}",
                                'lp_change': new_rank['lp'] - old_rank['lp']
                            })
                        else:
                            lp_change = new_rank['lp'] - old_rank['lp']
                            if lp_change != 0:
                                changes.append({
                                    'queue': queue_name,
                                    'change_type': 'lp',
                                    'tier': new_rank['tier'],
                                    'rank': new_rank['rank'],
                                    'lp_change': lp_change
                                })
        
        return changes if changes else None


    
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

    def add_notified_summoner(self, puuid, game_id, summoner_id):
        """Add a summoner to the notified list with their summoner_id"""
        if not any(entry['puuid'] == puuid and entry['game_id'] == game_id for entry in self.notified_summoners):
            self.notified_summoners.append({
                "puuid": puuid,
                "game_id": game_id,
                "summoner_id": summoner_id  # Using summoner_id instead of riot_id
            })
        print(f"Added summoner to notified_summoners with gameId: {game_id}")
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


