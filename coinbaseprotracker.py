import json, sys
import numpy as np
import pandas as pd
from models.CoinbasePro import AuthAPI as CBAuthAPI, PublicAPI as CBPublicAPI

def printHelp():
    print ('Create a config.json:')
    print ('* Add 1 or more portfolios', "\n")

    print ('{')
    print ('    "<portfolio_name>" : {')
    print ('        "api_key" : "<coinbase_pro_api_key>",')
    print ('        "api_secret" : "<coinbase_pro_api_secret>",')
    print ('        "api_pass" : "<coinbase_pro_api_passphrase>",')
    print ('        "config" : {')
    print ('            "base_currency" : "<base_symbol>",')
    print ('            "quote_currency" : "<quote_symbol>"')
    print ('        "}')
    print ('    },')
    print ('    "<portfolio_name>" : {')
    print ('        "api_key" : "<coinbase_pro_api_key>",')
    print ('        "api_secret" : "<coinbase_pro_api_secret>",')
    print ('        "api_pass" : "<coinbase_pro_api_passphrase>",')
    print ('        "config" : {')
    print ('            "base_currency" : "<base_symbol>",')
    print ('            "quote_currency" : "<quote_symbol>"')
    print ('        "}')
    print ('    }')
    print ('}', "\n")

    print ('<portfolio_name> - Coinbase Pro portfolio name E.g. "Default portfolio"')
    print ('<coinbase_pro_api_key> - Coinbase Pro API key for the portfolio')
    print ('<coinbase_pro_api_secret> - Coinbase Pro API secret for the portfolio')
    print ('<coinbase_pro_api_passphrase> - Coinbase Pro API passphrase for the portfolio')
    print ('<base_symbol> - Base currency E.g. BTC')
    print ('<quote_symbol> - Base currency E.g. GBP')
    print ("\n")

try:
    with open('config.json') as config_file:
        json_config = json.load(config_file)

    if not isinstance(json_config, dict):
        raise TypeError('config.json is invalid.')

    if len(list(json_config)) < 1:
        printHelp()
        sys.exit()

    df_tracker = pd.DataFrame()

    for portfolio in list(json_config):
        base_currency = ''
        quote_currency = ''
        market = ''

        portfolio_config = json_config[portfolio]

        if 'api_key' in portfolio_config and 'api_secret' in portfolio_config and 'api_pass' in portfolio_config and 'config' in portfolio_config:
            print ('=== ', portfolio, " =======================================================\n")

            api_key = portfolio_config['api_key']
            api_secret = portfolio_config['api_secret']
            api_pass = portfolio_config['api_pass']

            config = portfolio_config['config']
            if ('cryptoMarket' not in config and 'base_currency' not in config) and ('fiatMarket' not in config and 'quote_currency' not in config):
                printHelp()
                sys.exit()

            if 'cryptoMarket' in config:
                base_currency = config['cryptoMarket']
            elif 'base_currency' in config:
                base_currency = config['base_currency']

            if 'fiatMarket' in config:
                quote_currency = config['fiatMarket']
            elif 'base_currency' in config:
                quote_currency = config['quote_currency']

            market = base_currency + '-' + quote_currency

            api = CBAuthAPI(api_key, api_secret, api_pass)
            orders = api.getOrders(market)

            last_action = ''
            for market in orders['market'].sort_values().unique():
                df_market = orders[orders['market'] == market]

            df_buy = pd.DataFrame()
            df_sell = pd.DataFrame()

            pair = 0
            # pylint: disable=unused-variable
            for index, row in df_market.iterrows():
                if row['action'] == 'buy':
                    pair = 1

                if pair == 1 and (row['action'] != last_action):
                    if row['action'] == 'buy':
                        df_buy = row
                    elif row['action'] == 'sell':
                        df_sell = row
                            
                if row['action'] == 'sell' and len(df_buy) != 0:
                    df_pair = pd.DataFrame([
                        [
                            df_sell['status'], 
                            df_buy['market'], 
                            df_buy['created_at'], 
                            df_buy['type'], 
                            df_buy['size'],
                            df_buy['value'],
                            df_buy['fees'], 
                            df_buy['price'],
                            df_sell['created_at'],
                            df_sell['type'], 
                            df_sell['size'], 
                            df_sell['value'],
                            df_sell['fees'], 
                            df_sell['price']                    
                        ]], columns=[ 'status', 'market', 
                            'buy_at', 'buy_type', 'buy_size', 'buy_value', 'buy_fees', 'buy_price',
                            'sell_at', 'sell_type', 'sell_size', 'sell_value', 'sell_fees', 'sell_price' 
                        ])
                    
                    df_tracker = df_tracker.append(df_pair, ignore_index=True)
                    pair = 0
                
                last_action = row['action']

            fees = api.authAPI('GET', 'fees')
            maker_fee_rate = float(fees['maker_fee_rate'].to_string(index=False).strip())
            taker_fee_rate = float(fees['maker_fee_rate'].to_string(index=False).strip())

            if len(orders) > 0:
                last_order = orders.iloc[-1:]
                last_buy_order = last_order[last_order.action == 'buy']
                last_buy_order = last_buy_order.reset_index(drop=True)

                if len(last_buy_order) > 0:
                    print (last_buy_order.to_string(index=False))

                    market = last_buy_order['market'].to_string(index=False).strip()
                    order_type = last_buy_order['type'].to_string(index=False).strip()
                    size = float(last_buy_order['size'].to_string(index=False).strip())
                    value = float(last_buy_order['value'].to_string(index=False).strip())
                    price = float(last_buy_order['price'].to_string(index=False).strip())
                    
                    api = CBPublicAPI()
                    ticker = api.getTicker(market)
                    current_value = ticker * size

                    maker_sale_fees = current_value * maker_fee_rate
                    taker_sale_fees = current_value * taker_fee_rate

                    maker_net_profit = current_value - value - maker_sale_fees
                    maker_margin = (current_value - value - maker_fee_rate) / current_value * 100

                    taker_net_profit = current_value - value - taker_sale_fees
                    taker_margin = (current_value - value - taker_fee_rate) / current_value * 100

                    if isinstance(ticker, float): 
                        print ("\n", "       Current Price :", "{:.2f}".format(ticker))

                        print ("\n", "      Purchase Value :", "{:.2f}".format(value))
                        print (     "        Current Value :", "{:.2f}".format(current_value))

                        print ("\n", "      Maker Sale Fee :", "{:.2f}".format(maker_sale_fees), '(', str(maker_fee_rate), ')')
                        print (     "       Taker Sale Fee :", "{:.2f}".format(taker_sale_fees), '(', str(taker_fee_rate), ')')

                        print ("\n", "        Maker Profit :", "{:.2f}".format(maker_net_profit))
                        print (     "         Maker Margin :", str("{:.2f}".format(maker_margin)) + '%')

                        print ("\n", "        Taker Profit :", "{:.2f}".format(taker_net_profit))
                        print (     "         Taker Margin :", str("{:.2f}".format(taker_margin)) + '%')

                else:
                    if len(orders) > 0:
                        second_last_order = orders.iloc[-2:]
                        last_buy_order = second_last_order[second_last_order.action == 'buy']
                        last_buy_order = last_buy_order.reset_index(drop=True)

                        if len(last_buy_order) > 0:
                            orders = api.getOrders(status='open')
                            if len(orders) == 1:
                                last_open_order = orders[orders.action == 'sell']
                                last_open_order = last_open_order.reset_index(drop=True)

                                print (last_buy_order.to_string(index=False))
                                print ("\n", last_open_order.to_string(index=False))
                                
                                market = last_buy_order['market'].to_string(index=False).strip()
                                order_type = last_buy_order['type'].to_string(index=False).strip()
                                size = float(last_buy_order['size'].to_string(index=False).strip())
                                value = float(last_buy_order['value'].to_string(index=False).strip())
                                price = float(last_buy_order['price'].to_string(index=False).strip())

                                future_value = float(last_open_order['value'].to_string(index=False).strip())

                                api = CBPublicAPI()
                                ticker = api.getTicker(market)
                                current_value = ticker * size

                                maker_sale_fees = future_value * maker_fee_rate
                                taker_sale_fees = current_value * taker_fee_rate

                                maker_net_profit = future_value - value - maker_sale_fees
                                maker_margin = (future_value - value - maker_fee_rate) / future_value * 100

                                taker_net_profit = current_value - value - taker_sale_fees
                                taker_margin = (current_value - value - taker_fee_rate) / current_value * 100

                                if isinstance(ticker, float): 
                                    print ("\n", "       Current Price :", "{:.2f}".format(ticker))

                                    print ("\n", "      Purchase Value :", "{:.2f}".format(value))
                                    print (     "        Current Value :", "{:.2f}".format(current_value))
                                    print (     "         Target Value :", "{:.2f}".format(future_value))

                                    print ("\n", "      Maker Sale Fee :", "{:.2f}".format(maker_sale_fees), '(', str(maker_fee_rate), ')')
                                    print (     "       Taker Sale Fee :", "{:.2f}".format(taker_sale_fees), '(', str(taker_fee_rate), ')')

                                    print (     "         Taker Profit :", "{:.2f}".format(taker_net_profit), '(now)')
                                    print (     "         Taker Margin :", str("{:.2f}".format(taker_margin)) + '%', '(now)')

                                    print (     "         Maker Profit :", "{:.2f}".format(maker_net_profit), '(target)')
                                    print (     "         Maker Margin :", str("{:.2f}".format(maker_margin)) + '%', '(target)')

                            else:
                                print ('*** no active position open ***')

                        else:
                            print ('*** no active position open ***')

                    else:
                        print ('*** no active position open ***')
            
            print ("\n")
        else:
            printHelp()
            sys.exit()

        #break

    df_tracker = df_tracker[df_tracker['status'] == 'done']
    df_tracker['profit'] = np.subtract(np.subtract(df_tracker['sell_value'], df_tracker['buy_value']), np.add(df_tracker['sell_fees'], df_tracker['buy_fees']))
    df_tracker['margin'] = np.multiply(np.true_divide(df_tracker['profit'], df_tracker['buy_value']), 100)
    df_sincebot = df_tracker[df_tracker['buy_at'] > '2021-02-1']
    save_file = 'tracker.csv'

    try:
        df_sincebot.to_csv(save_file, index=False)
    except OSError:
        raise SystemExit('Unable to save: ', save_file) 

except IOError as err:
    print (err)
except Exception as err:
    print (err)