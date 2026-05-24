ue_url_base = 'http://172.168.21.244:15935'
# ue_url_base = 'http://172.168.21.242:15935'
# ue_url_base = 'http://172.168.21.160:15935'
# ue_url_base = 'http://172.168.20.169:15935'

# 数据库ip
db_ip = '172.168.20.151'

#场景部署相关
url_map = ue_url_base + '/map/?map_name='
url_chageWearher = ue_url_base + '/ChangeWeather'
url_chageData =  ue_url_base + '/ChangeDate'

#控制导条相关
url_controlModulation =  ue_url_base + "/Gamestate/ChangeSim?SimState="

# 兵力部署相关
url_dispose = ue_url_base + '/Equipment/Spawn'
url_remove = ue_url_base + '/Equipment/RemoveByID'
url_modify = ue_url_base + '/Equipment/ChangeLocation'
url_attr = ue_url_base + '/Equipment/ChangeAttribute'


# 行为配置相关
url_setbehavior = ue_url_base + "/Equipment/SetBehavior"
url_GetUEInfo = ue_url_base + "/Equipment/GetInfo/"
url_UELocation2LonLat = ue_url_base + "/Misc/GetLonLatByUELocation"

#语音转文字
url_voice2text = "http://172.168.20.153:7018/inference"

#获取UE兵力
url_getEntity = ue_url_base+"/Equipment/GetInfo/"