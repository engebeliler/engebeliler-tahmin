import pandas as pd
from supabase_client import supabase


def init_db():
    pass


def get_users():
    return supabase.table("users").select("*").execute().data


def get_matches():
    return supabase.table("matches").select("*").execute().data


def get_predictions():
    return supabase.table("predictions").select("*").execute().data


def add_user(username, password, role="user"):
    return supabase.table("users").insert({
        "username": username,
        "password": password,
        "role": role
    }).execute()


def add_match(home_team, away_team, match_type="Normal"):
    return supabase.table("matches").insert({
        "home_team": home_team,
        "away_team": away_team,
        "match_type": match_type
    }).execute()


def set_setting(key, value):
    return supabase.table("settings").upsert({
        "key": key,
        "value": value
    }).execute()


def get_setting(key):
    result = (
        supabase
        .table("settings")
        .select("*")
        .eq("key", key)
        .execute()
    )

    if result.data:
        return result.data[0]["value"]

    return ""