from config.global_conf import Global

Global.send_to_slack_channel(Global.SLACK_STREAM_STATUS_URL, "test")
Global.send_to_slack_channel(Global.SLACK_BOT_STATUS_URL, "test")
Global.send_to_slack_channel(Global.SLACK_OTC_SCHEDUELR_URL, "test")
Global.send_to_slack_channel(Global.SLACK_BAL_STATUS_URL, "test")