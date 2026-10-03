import cdsapi

client = cdsapi.Client()

dataset = "tigge-forecasts"

request = {
    "class": "ti",
    "date": "2024-08-15",
    "expver": "prod",
    "grid": "0.5/0.5",
    "levtype": "sfc",
    "origin": "ecmf",
    "param": "167",
    "step": "24",
    "time": "00:00:00",
    "type": "cf",
}

target = "tigge_test.grib"

print("Submitting TIGGE request...")
client.retrieve(dataset, request, target)

print("SUCCESS")
print("Downloaded:", target)