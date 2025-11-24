## Importando as bibliotecas
import pandas as pd
import numpy as np
import requests

# Chamandos os endpoints da nba_api
from nba_api.stats.endpoints import leaguedashteamstats
from nba_api.stats.endpoints import commonplayoffseries
from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguedashteamshotlocations
from nba_api.stats.endpoints import leaguedashplayerstats


nba_teams = [
    # Conferência Leste
    "ATLANTA HAWKS", "BOSTON CELTICS", "BROOKLYN NETS", "CHARLOTTE HORNETS", 
    "CHICAGO BULLS", "CLEVELAND CAVALIERS", "DETROIT PISTONS", "INDIANA PACERS", 
    "MIAMI HEAT", "MILWAUKEE BUCKS", "NEW YORK KNICKS", "ORLANDO MAGIC", 
    "PHILADELPHIA 76ERS", "TORONTO RAPTORS", "WASHINGTON WIZARDS",
    
    # Conferência Oeste
    "DALLAS MAVERICKS", "DENVER NUGGETS", "GOLDEN STATE WARRIORS", "HOUSTON ROCKETS", 
    "LOS ANGELES CLIPPERS", "LOS ANGELES LAKERS", "MEMPHIS GRIZZLIES", 
    "MINNESOTA TIMBERWOLVES", "NEW ORLEANS PELICANS", "OKLAHOMA CITY THUNDER", 
    "PHOENIX SUNS", "PORTLAND TRAIL BLAZERS", "SACRAMENTO KINGS", 
    "SAN ANTONIO SPURS", "UTAH JAZZ"
]


def find_ID_by_name(team_name):
    team_infos = teams.find_teams_by_full_name(team_name)
    return team_infos[0]["id"]

def find_abb_by_name(team_name):
    team_infos = teams.find_teams_by_full_name(team_name)
    return team_infos[0]["abbreviation"]

def getting_ID_row_by_name(teams_Series, df_teams):
    dict_times_ids = {}
    for time in teams_Series:
        dict_times_ids[time] = find_ID_by_name(time)

    for time in df_teams["TEAMS"]:
        for k in dict_times_ids.keys():
            if time == k:
                df_teams.loc[df_teams["TEAMS"] == time, "TEAM_ID"] = str(dict_times_ids[time])


# Obtendo EFG_PCT, FT_RATE, ORB% e TOV%
def get_four_factors(season):
    four_factors = leaguedashteamstats.LeagueDashTeamStats(
    season=season, 
    measure_type_detailed_defense='Four Factors').get_data_frames()[0]
    cols_interesse = ["TEAM_ID", "EFG_PCT", "FTA_RATE", "OREB_PCT", "TM_TOV_PCT"]
    return four_factors[cols_interesse]


# Obtendo OFF_RATING, DEF_RATING, NET_RATING, AST% E PACE.
def get_advanced_stats(season):
    adv_stats = leaguedashteamstats.LeagueDashTeamStats(
    season=season, 
    measure_type_detailed_defense='Advanced').get_data_frames()[0]
    cols_interesse = ['TEAM_ID', 'OFF_RATING', 'DEF_RATING', 'NET_RATING', 'AST_PCT', 'PACE']
    return adv_stats[cols_interesse]


# Obtendo 3PT_RATE
def get_scoring_stats(season):
    scoring_stats = leaguedashteamstats.LeagueDashTeamStats(
    season=season, 
    measure_type_detailed_defense='Scoring').get_data_frames()[0]
    cols_interesse = ["TEAM_ID", 'PCT_FGA_3PT']
    return scoring_stats[cols_interesse]


# Obtendo BENCH_PTS%
def get_bench_point_percent(season):
    bench = leaguedashteamstats.LeagueDashTeamStats(
        season=season, 
        measure_type_detailed_defense='Base',
        starter_bench_nullable='Bench').get_data_frames()[0]
    
    team = leaguedashteamstats.LeagueDashTeamStats(
        season=season, 
        measure_type_detailed_defense='Base',
    ).get_data_frames()[0]

    cols_bench = ["TEAM_ID", 'PTS']
    cols_team = ["TEAM_ID", 'PTS']
    bench = bench[cols_bench]
    bench = bench.rename(columns={'PTS':'PTS_BENCH'})
    team = team[cols_team]
    df_total = pd.merge(bench, team, on="TEAM_ID")
    df_total["BENCH_PTS_PCT"] = (df_total["PTS_BENCH"] / df_total["PTS"])
    df_total = df_total.drop(columns={"PTS_BENCH", "PTS"})
    return df_total


# Obtendo STEAL% E BLK%
def get_shot_locations_pct(season):
    shot_locs = leaguedashteamshotlocations.LeagueDashTeamShotLocations(
        season=season,
        measure_type_simple='Base'
    ).get_data_frames()[0]
    all_shots =  leaguedashteamstats.LeagueDashTeamStats(
        season=season, 
        measure_type_detailed_defense='Base',
    ).get_data_frames()[0]

    # Fazendo as colunas de interesse (nessa função, elas estão em tuplas)
    col_ra= [('Restricted Area', 'FGA')]
    col_mid_range = [('Mid-Range', 'FGA')]
    col_id = [('', 'TEAM_ID')]

    # Inserindo as colunas no nosso DataFrame
    df_total = pd.DataFrame()
    df_total["MIDRANGE_FGA"] = shot_locs[col_mid_range]
    df_total["RIM_FGA"] = shot_locs[col_ra]
    df_total["FGA"] = all_shots["FGA"]

    # Calculando o RIM% e MID-RANGE%
    df_final = pd.DataFrame()
    df_final["TEAM_ID"] = shot_locs[col_id]
    df_final["RIM_PCT"] = df_total["RIM_FGA"] / df_total['FGA']
    df_final["MID_PCT"] = df_total["MIDRANGE_FGA"] / df_total['FGA']

    return df_final


def get_usage_stars(season, min_games=30):

    # Criando um df_teams (auxiliar)
    df_teams = pd.DataFrame()
    df_teams["TEAMS"] = nba_teams
    getting_ID_row_by_name(df_teams["TEAMS"], df_teams)
    df_teams

    df = leaguedashplayerstats.LeagueDashPlayerStats(
        season=season,
        per_mode_detailed='PerGame',
        measure_type_detailed_defense='Advanced' 
    ).get_data_frames()[0]

    cols = ["PLAYER_NAME", "TEAM_ID", "TEAM_ABBREVIATION", "GP", "USG_PCT"]
    metric = "USG_PCT"

    df = df[cols]
    df_filtered = df[df['GP'] >= min_games].copy()
    team_ids = df_teams["TEAM_ID"].astype(int)

    # Criando listas que servirão de colunas para o df final
    leader1_name = []
    leader2_name = []
    leader1_usg = []
    leader2_usg = []
    

    for team_id in team_ids:
        team_df = df_filtered[df_filtered['TEAM_ID'] == team_id]
        
        # Cria um DataFrame ordenado pelos 2 jogadores com mais USG%
        top_2 = team_df.sort_values(by=metric, ascending=False).head(2)
        
        players_name = []
        players_usg = []
        for index, player in top_2.iterrows(): # Index iterando as linhas
            usg_val = player[metric]
            players_name.append(player['PLAYER_NAME'])
            players_usg.append(round(usg_val, 1))

        leader1_usg.append(players_usg[0])
        leader2_usg.append(players_usg[1])
        leader1_name.append(players_name[0])
        leader2_name.append(players_name[1])
        
    df_results = pd.DataFrame()
    df_results["TEAM_NAME"] = nba_teams
    df_results["LEADER 1"], df_results["USG_L1"]= leader1_name, leader2_name
    df_results["LEADER 2"], df_results["USG_L2"] = leader1_usg, leader2_usg
    return df_results