import cdsapi

client = cdsapi.Client(
    url="https://ecds.ecmwf.int/api"
)

request = {
    "class": "ti",
    "date": "2020-06-01",
    "expver": "prod",
    "levtype": "sfc",
    "origin": "ecmf",

    # TIGGE parameter IDs
    "param": "165/166/167/168/151/228228",

    # 6h -> 24h for initial test
    "step": "6/12/18/24",

    "stream": "enfo",
    "time": "12:00:00",
    "type": "cf",

    # N / W / S / E
    "area": "38/65/5/100",
}

target = "ecmwf_multi_test.grib"

print("Submitting ECMWF multi-variable TIGGE test...")

client.retrieve(
    "tigge-forecasts",
    request,
    target
)

print("SUCCESS")
print("Downloaded:", target)