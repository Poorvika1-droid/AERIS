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
    "param": "167",
    "step": "6",
    "stream": "enfo",
    "time": "12:00:00",
    "type": "cf",
    "area": "38/65/5/100",
}

target = "ecmwf_test_t2m.grib"

print("Submitting ECMWF TIGGE test...")

client.retrieve(
    "tigge-forecasts",
    request,
    target
)

print("SUCCESS")
print("Downloaded:", target)