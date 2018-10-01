from config.config_market_manager import ConfigMarketManager

mm1 = getattr(ConfigMarketManager, "BITHUMB").value
print(mm1)
