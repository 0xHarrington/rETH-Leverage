from app.api import * 
from app.models import *
import pandas as pd
from flask import Flask
from app.historical_data import scrape_historic_all
from app.supply_and_borrow_transactions import supply_transactions
from app.user_history import user_history
from app.leveraged_users import leveraged_users_by_market
from app.transactions_network_generator import generate_network
import pandas as pd
import json
import schedule
import time
from datetime import datetime, timezone, timedelta

def create_app():
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
    db.init_app(app)
    app.register_blueprint(api, url_prefix="/api")
    return app

app = create_app()

def create_tables():
    """
    Create database tables based on SQLAlchemy models.
    """
    with app.app_context():
        db.create_all()

def add_dataframe_to_db(df, model, table_name):
    """
    Add a pandas DataFrame to the corresponding SQLAlchemy model table in the database.

    Args:
        df (pandas.DataFrame): The DataFrame to be added to the database.
        model (SQLAlchemy model): The SQLAlchemy model representing the database table.
        table_name (str): The name of the table to which the DataFrame will be added.

    Returns:
        bool: True if the DataFrame was successfully added to the database, False otherwise.
    """
    with app.app_context():
        try:
            create_tables()
            # Replace NaN values with None
            df = df.where(pd.notnull(df), None)
            # Write DataFrame to SQL table
            df.to_sql(table_name, con=db.engine, if_exists='replace', index=False)
            return True
        except Exception as e:
            print(f"Error adding DataFrame to database: {e}")
            return False
        
def read_historical_data():
    with app.app_context():
        engine = db.engine.connect()
        df = pd.read_sql_table('HistoricalData', con=engine)
        return df


global_all_markets = ['AAVE', 'COMPOUND', 'PRISMA']

# Function to initialize tables
def db_init():
    print('Database initialization starting at (UTC): ', datetime.utcnow().isoformat())

    # Scrape Historic Data: (non-computed values)
    historic_data = scrape_historic_all(timeframe=1)
    add_dataframe_to_db(historic_data, HistoricalData, 'HistoricalData')
    historic_data.to_csv(f'./db_backups/historic_data_{datetime.utcnow().timestamp()}.csv', index=False)

    # Get all leveraged users over all markets
    leveraged_users = []
    for market in global_all_markets:
        # Get suppliers of rETH for this market
        supply_data = supply_transactions(market=market, timeframe=1, token='rETH')

        # Grab leveraged user list for this market
        if not supply_data.empty:
            leveraged_users.extend(leveraged_users_by_market(market=market, supplied_transactions=supply_data))

    # Get user history for over-leveraged users
    interaction_dict = user_history(user_addresses=leveraged_users, markets=global_all_markets)
    all_dfs = []
    for key, dfs_list in interaction_dict.items():
        # Concatenate all DataFrames in the list for the current wallet address
        if len(dfs_list) != 0:
            combined_df = pd.concat(dfs_list, ignore_index=True)
            all_dfs.append(combined_df)

    # Concatenate all combined DataFrames into one
    if len(all_dfs) != 0:
        transaction_df = pd.concat(all_dfs, ignore_index=True)
        transaction_df['Amount'] = transaction_df['Amount'] / 10**18
        transaction_df['Borrow Rate'] = transaction_df['Borrow Rate'] / 10**27
        add_dataframe_to_db(transaction_df, UserHistory, 'UserHistory')
        transaction_df.to_csv(f'./db_backups/user_history_{datetime.utcnow().timestamp()}.csv', index=False)

        # Generate network graph with user histories
        graph_data = generate_network(transaction_df)
        with open('./network_graph.json', 'w') as f:
            json.dump(graph_data, f, indent=4)

    print('Database initialization complete at (UTC): ', datetime.utcnow().isoformat())
    print()


# Helpers for update function
def round_to_previous_six_hour_interval(now):
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    seconds_since_midnight = int((now - midnight).total_seconds())
    seconds_per_interval = 6 * 3600
    rounded_seconds = seconds_since_midnight // seconds_per_interval * seconds_per_interval
    rounded_time = midnight + timedelta(seconds=rounded_seconds)
    rounded_timestamp = int(rounded_time.timestamp())

    return rounded_timestamp

def round_to_nearest_six_hours(timestamp):
    utc_datetime = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    hours_since_midnight = utc_datetime.hour + utc_datetime.minute / 60 + utc_datetime.second / 3600
    nearest_interval = round(hours_since_midnight / 6) * 6
    if nearest_interval == 24:
        nearest_interval = 0
    rounded_datetime = utc_datetime.replace(hour=int(nearest_interval), minute=0, second=0, microsecond=0)
    if nearest_interval < hours_since_midnight:
        rounded_datetime += timedelta(hours=6)
    return int(rounded_datetime.timestamp())


def db_update():
    print('Database update starting at (UTC): ', datetime.utcnow().isoformat())

    # Update historic data table
        # Get last 6 hours of data and append to existing table
    new_historic_data = scrape_historic_all(timeframe=1).sort_values('Timestamp', ascending=True)
    x = round_to_previous_six_hour_interval(datetime.now(timezone.utc))
    y = x - (6 * 3600)
    historic_data_update = new_historic_data[new_historic_data['Timestamp'] >= y]
    curr_historic_data = read_historical_data()
    # curr_historic_data = pd.read_csv('./historic_data.csv')
    temp = pd.concat([curr_historic_data, historic_data_update], ignore_index=True)
        # Remove first 6 hours of data from temp
    earliest = round_to_nearest_six_hours(temp.iloc[0]['Timestamp'])
    z = earliest + (6 * 3600)
    temp = temp[temp['Timestamp'] >= z]
        # Store as new table
    add_dataframe_to_db(temp, HistoricalData, 'HistoricalData')
    temp.to_csv(f'./db_backups/historic_data_{datetime.utcnow().timestamp()}.csv', index=False)

    # Update user history table
    # Get all leveraged users over all markets
    leveraged_users = []
    for market in global_all_markets:
        # Get suppliers of rETH for this market
        supply_data = supply_transactions(market=market, timeframe=1, token='rETH')

        # Grab leveraged user list for this market
        if not supply_data.empty:
            leveraged_users.extend(leveraged_users_by_market(market=market, supplied_transactions=supply_data))

    # New user history
    interaction_dict = user_history(user_addresses=leveraged_users, markets=global_all_markets)
    all_dfs = []
    for key, dfs_list in interaction_dict.items():
        # Concatenate all DataFrames in the list for the current wallet address
        if len(dfs_list) != 0:
            combined_df = pd.concat(dfs_list, ignore_index=True)
            all_dfs.append(combined_df)

    # Concatenate all combined DataFrames into one
    if len(all_dfs) != 0:
        transaction_df = pd.concat(all_dfs, ignore_index=True)
        transaction_df['Amount'] = transaction_df['Amount'] / 10**18
        transaction_df['Borrow Rate'] = transaction_df['Borrow Rate'] / 10**27
        add_dataframe_to_db(transaction_df, UserHistory, 'UserHistory')
        transaction_df.to_csv(f'./db_backups/user_history_{datetime.utcnow().timestamp()}.csv', index=False)

        # Generate network graph with user histories
        graph_data = generate_network(transaction_df)
        with open('./network_graph.json', 'w') as f:
            json.dump(graph_data, f, indent=4)

    print('Database update complete at (UTC): ', datetime.utcnow().isoformat())
    print()

# Initialize database
db_init()

# Schedule database updates to every 6 hours (SET TO SYSTEM TIME ZONE)
schedule.every().day.at("00:05").do(db_update)
schedule.every().day.at("06:05").do(db_update)
schedule.every().day.at("12:05").do(db_update)
schedule.every().day.at("18:05").do(db_update)

while True:
    schedule.run_pending()
    time.sleep(10)
