import requests
import json
import random
from time import sleep

# Get from: https://steamcommunity.com/saliengame/gettoken
TOKEN = ""

# Don't edit stuff below
class ApiException(Exception):
    """General API Exception"""
    pass

class GetZoneException(ApiException):
    """Exception with get_zone"""
    pass

class GetUserInfoException(ApiException):
    """Exception with get_user_info"""
    pass

class LeavePlanetException(ApiException):
    """Exception with leave_game"""
    pass

class JoinPlanetException(ApiException):
    """Exception with join_planet"""
    pass

class JoinZoneException(ApiException):
    """Exception with join_zone"""
    pass

class ReportScoreException(ApiException):
    """Exception with report_score"""
    pass

SCORE_TABLE = [None, 600, 1200, 2400, 4800]
RANDOMIZE = True

s = requests.session()
s.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/67.0.3396.87 Safari/537.36',
    'Referer': 'https://steamcommunity.com/saliengame/play/',
    'Origin': 'https://steamcommunity.com',
    'Accept': '*/*'
    })

def get_zone():
    data = {'active_only': 1}
    result = s.get("https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanets/v0001/", params=data)
    if result.status_code != 200:
        raise GetZoneException('Status code: {}'.format(results.status_code))
    json_data = result.json()

    candidates = []
    for planet in json_data["response"]["planets"]:
        info_data = {'id': planet["id"]}
        info = s.get("https://community.steam-api.com/ITerritoryControlMinigameService/GetPlanet/v0001/", params=info_data)
        if info.status_code != 200:
            print("Get planet errored... trying the next planet")
            continue
        info_json = info.json()
        for zone in info_json["response"]["planets"][0]["zones"]:
            if not zone["captured"] and zone["capture_progress"] < 0.9:
                candidates.append((zone["difficulty"],
                    random.random() if RANDOMIZE else 0,
                    zone["zone_position"],
                    (planet["id"], planet["state"]["name"])))
    return sorted(candidates, reverse = True)[0]

def get_user_info():
    data = {'access_token': TOKEN}
    result = s.post("https://community.steam-api.com/ITerritoryControlMinigameService/GetPlayerInfo/v0001/", data=data)
    if result.status_code != 200:
        raise GetUserInfoException("Status code: {}".format(result.status_code))
    if "active_zone_game" in result.json()["response"]:
        current_zone = result.json()["response"]["active_zone_game"]
        print("Leaving zone {}".format(current_zone))
        leave_game(current_zone)
    if "active_planet" in result.json()["response"]:
        return result.json()["response"]["active_planet"]
    else:
        return None

def leave_game(current):
    data = {
        'gameid': current,
        'access_token': TOKEN
    }
    result = s.post("https://community.steam-api.com/IMiniGameService/LeaveGame/v0001/", data = data)
    if result.status_code != 200:
        raise LeavePlanetException("Status code: {}".format(result.status_code))

def join_planet(planet_id, planet_name):
    data = {
        'id': planet_id,
        'access_token': TOKEN
    }
    result = s.post("https://community.steam-api.com/ITerritoryControlMinigameService/JoinPlanet/v0001/", data=data)
    if result.status_code != 200:
        raise JoinPlanetException("Status code: {}".format(result.status_code))
    else:
        print("Joined planet: ({}) {}".format(planet_id, planet_name))

def join_zone(zone):
    data = {
        'zone_position': zone,
        'access_token': TOKEN
    }
    result = s.post("https://community.steam-api.com/ITerritoryControlMinigameService/JoinZone/v0001/", data=data)
    if result.status_code != 200 or result.json() == {'response':{}}:
        raise JoinZoneException("Status code: {}".format(result.status_code))
    else:
        print("Joined zone: {}".format(result.json()["response"]["zone_info"]["zone_position"]))


def report_score(difficulty = 3):
    try:
        score = SCORE_TABLE[difficulty]
    except Exception:
        raise ReportScoreException("Attempting to report a score for invalid difficulty {}".format(difficulty))
    data = {
        'access_token': TOKEN,
        'score': score,
        'language':'english'
    }
    if data['score'] is None:
        raise ReportScoreException("Attempting to report a score for invalid difficulty {}".format(difficulty))
    result = s.post("https://community.steam-api.com/ITerritoryControlMinigameService/ReportScore/v0001/", data=data)
    if result.status_code != 200 or result.json() == {'response':{}}:
        raise ReportScoreException("Status code: {}".format(result.status_code))
    else:
        res = result.json()["response"]
        score_delta = int(res["next_level_score"]) - int(res["new_score"])
        eta_seconds = int(score_delta / score) * 110
        days, hours, minutes = eta_seconds / 86400, (eta_seconds % 86400) / 3600, (eta_seconds % 3600) / 60
        print("Level: {} | Score: {} -> {} | Level up ETA: {}{:0>2}:{:0>2} {}".format(
            res["new_level"],
            res["old_score"],
            res["new_score"],
            "{}d ".format(days) if days > 0 else "",
            hours,
            minutes,
            "Level UP!" if res["old_level"] != res["new_level"] else ""))

def play_game(explore_threshold = 10):
    current = get_user_info()
    if not current is None:
        print("Leaving current planet")
        leave_game(current)
    print("Finding a planet and zone")
    difficulty, _, zone, planet = get_zone()
    planet_id, planet_name = planet
    join_planet(planet_id, planet_name)
    
    low_difficulty_count = 0
    while low_difficulty_count < explore_threshold:
        low_difficulty_count = (low_difficulty_count + 1) if difficulty < 3 else 0
        print("Joining zone {} @ {} with difficulty {}".format(zone, planet_name, difficulty))
        join_zone(zone)
        print("Sleeping for 1 minute 50 seconds")
        sleep(110)
        report_score(difficulty)

if __name__ == "__main__":
    while True:
        try:
            play_game()
        except ApiException as e:
            print("Exception with API. Restarting round of game in 10s")
            sleep(10)
            continue
        except KeyboardInterrupt:
            print("User cancelled script. Cleanup before exiting.")
            exit(1)
        except Exception as e:
            print e
            continue