import asyncio
from riot_api import requestSummonerTFT, fetchRanksTFT, fetchGameOngoingTFT
from dotenv import load_dotenv

async def test_tft_lookup():
    try:
        # Test cases - add more summoners as needed
        test_cases = [
            ("Ch Pain Perdu", "EUW"),
            ("B2 Byss", "EUW"),
            # Add more test cases here
        ]

        for name, tag in test_cases:
            print(f"\nTesting TFT lookup for {name}#{tag}")
            try:
                summoner_data = await requestSummonerTFT(name, tag)
                print(f"Summoner data: {summoner_data}")

                # If you want to test ranks too
                if summoner_data:
                    tft_id = summoner_data[4]  # Adjust index based on your return structure
                    ranks = fetchRanksTFT(tft_id)
                    print(f"TFT Ranks: {ranks}")

            except Exception as e:
                print(f"Error testing {name}#{tag}: {e}")

    except Exception as e:
        print(f"General error: {e}")
        
async def test_tft_game():
    try:
        # Test cases
        test_cases = [
            ("B2 Byss", "EUW"),
            ("AEG mistermv", "EUW"),
        ]

        for name, tag in test_cases:
            print(f"\nTesting TFT game status for {name}#{tag}")
            try:
                # Get summoner data
                summoner_data = await requestSummonerTFT(name, tag)
                print(f"Raw summoner data: {summoner_data}")
                
                if summoner_data:
                    tag = summoner_data[0]
                    summoner_name = summoner_data[1]
                    puuid = summoner_data[5]
                    
                    print(f"Tag: {tag}")
                    print(f"Name: {summoner_name}")
                    print(f"PUUID: {puuid}")

                    # Check if they're in a game
                    try:
                        game_data = fetchGameOngoingTFT(puuid)
                        print(f"Game data: {game_data}")
                        
                        if game_data and game_data != (None, None, None, None, None):
                            summoner_name, tactician_name, game_mode, game_id, tactician_icon = game_data
                            print(f"\nGame found:")
                            print(f"Summoner Name: {summoner_name}")
                            print(f"Tactician: {tactician_name}")
                            print(f"Game Mode: {game_mode}")
                            print(f"Game ID: {game_id}")
                            print(f"Tactician Icon: {tactician_icon}")
                        else:
                            print("Summoner is not currently in a TFT game")
                    except Exception as game_error:
                        if "404" in str(game_error):
                            print("Summoner is not currently in a TFT game")
                        else:
                            print(f"Error checking game status: {game_error}")
                else:
                    print("No summoner data returned")

            except ValueError as ve:
                print(f"Summoner not found: {name}#{tag}")
                print(f"Error: {ve}")
            except Exception as e:
                print(f"Error testing {name}#{tag}: {e}")
                import traceback
                print(traceback.format_exc())

    except Exception as e:
        print(f"General error: {e}")

# Run the test
if __name__ == "__main__":
    asyncio.run(test_tft_game())