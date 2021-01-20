const API_URL = "/api/v1/mawaqit";
const SALAWAT_NAMES = {
    "fajr": "الفجر",
    "chorok": "الشروق",
    "dhohr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "icha": "العشاء"
};
const DATE_FORMAT = "yyyy-mm-dd";
const GEO_API_URL = "https://nominatim.openstreetmap.org/reverse";

// keep track of wilaya got from geo API to avoid sending requests if the wilaya didn't change
var geolocated_wilaya;

// keep track of current selected params to avoid sending requests if user selects the same values
var current_params = {};

async function fetchOneMawaqit(params) {
    let searchParams = new URLSearchParams(params);
    let url = API_URL + "?" + searchParams.toString();

    let response = await fetch(url)
        .catch(function(error) {
            console.error(error);
        });
    let mawaqit_list = await response.json();
    let mawaqit = mawaqit_list[0];
    return mawaqit;
}

function updateMawaqit(mawaqit, salawat = SALAWAT_NAMES) {
    for (const salat in salawat) {
        $(`#${salat}`).text(mawaqit[salawat[salat]]);
    }
}

async function refreshMawaqit() {
    let wilaya = $("#wilaya").val();
    let date = $("#datepicker").val();
    let params = {
        wilayas: wilaya,
        days: date,
    };
    // Skip updating if params doens't changed
    if (JSON.stringify(params) !== JSON.stringify(current_params)) {
        console.log('Updating mawaqit for', params);
        let mawaqit = await fetchOneMawaqit(params);
        updateMawaqit(mawaqit);
        current_params = params;
    }
}

function getWilayaFromLocation() {
    if (geolocated_wilaya !== $("#wilaya").val()) {
        navigator.geolocation.getCurrentPosition(async function callback(position) {
            params = new URLSearchParams({
                lat: position.coords.latitude,
                lon: position.coords.longitude,
                format: "json",
                "accept-language": "ar",
            });
            let url = GEO_API_URL + '?' + params.toString();
            let response = await fetch(url)
                .catch(function(error) {
                    console.error(error);
                });
            let response_object = await response.json();
            let wilaya_name = response_object.address.state;
            console.log("Setting wilaya to ", wilaya_name);
            $("#wilaya").selectpicker("val", wilaya_name).change();
            geolocated_wilaya = wilaya_name;
        });
    }
}

formatDate = (date) => date.toISOString().substring(0, 10);

$("#wilaya").change(refreshMawaqit);
$("#datepicker").change(refreshMawaqit);
$("#find-my-wilaya").click(getWilayaFromLocation);

$(function () {
    let today = formatDate(new Date());
    $("#datepicker").datepicker({
        uiLibrary: 'bootstrap4',
        format: DATE_FORMAT,
        value: today,
    });
    refreshMawaqit();
});
