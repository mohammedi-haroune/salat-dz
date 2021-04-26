const API_URL = "/api/v1/mawaqit";
const SAVE_URL = "/save";
const SALAWAT_NAMES = {
    "fajr": "الفجر",
    "chorok": "الشروق",
    "dhohr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "icha": "العشاء"
};
const DATE_COLUMN = "الموافق";
const WILAYA_COLUMN = "الولاية";
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
        .catch(function (error) {
            console.error(error);
        });
    let mawaqit_list = await response.json();
    let mawaqit = mawaqit_list[0];
    return mawaqit;
}

async function fetchNextSalat(wilaya) {
    let params = {
        wilayas: wilaya,
        salawat: 'next',
    };
    let mawaqit = await fetchOneMawaqit(params);

    delete mawaqit[DATE_COLUMN];
    delete mawaqit[WILAYA_COLUMN];

    let keys = Object.keys(mawaqit);
    if (keys.length == 1) {
        return keys[0];
    } else {
        return undefined;
    }
}

async function saveWilaya() {
    let wilaya = $("#wilaya").val();
    let searchParams = new URLSearchParams({ wilaya: wilaya });
    let url = SAVE_URL + "?" + searchParams.toString();

    try {
        const response = await fetch(url);
        if (response.ok) {
            $("#saved-toast").toast('show');
            console.log("Wilaya", wilaya, "saved, response:", response);
        } else {
            console.error(response);
        }
    } catch (error) {
        console.error(error);
    }
}

function dateDiff(d1, d2) {
    let DateDiff = {
        minutes: function (d1, d2) {
            var t1 = d1.getTime();
            var t2 = d2.getTime();
            return parseInt((t2 - t1) / 60000);
        },

        hours: function (d1, d2) {
            var t1 = d1.getTime();
            var t2 = d2.getTime();
            return parseInt((t2 - t1) / 3600000);
        }
    };

    var duration = "";

    var minutes = DateDiff.minutes(d1, d2);
    var hours = DateDiff.hours(d1, d2);

    if (minutes >= 60) {
        duration = `${hours}h`;

        minutes = minutes - hours * 60;
        if (minutes > 0) {
            duration = duration + `${minutes}m`;
        }
    } else {
        duration = `${minutes}m`;
    }

    return duration;
}

function updateMawaqit(mawaqit, nextSalat = undefined, salawat = SALAWAT_NAMES) {
    for (const englishName in salawat) {
        let arabicName = salawat[englishName];
        $(`#${englishName}`).text(mawaqit[arabicName]);

        if (arabicName == nextSalat) {
            let now = new Date();

            let [hours, minutes] = mawaqit[arabicName].split(':');
            let date = new Date(now.getTime());
            date.setHours(hours);
            date.setMinutes(minutes);

            let duration = dateDiff(now, date);

            let text = $(`#${englishName}`).text() + ` (${duration})`;
            $(`#${englishName}`).text(text);
        }
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
        let nextSalat = await fetchNextSalat(wilaya);
        updateMawaqit(mawaqit, nextSalat = nextSalat);
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
                .catch(function (error) {
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
$("#save-my-wilaya").click(saveWilaya);

$(function () {
    let today = formatDate(new Date());
    $("#datepicker").datepicker({
        uiLibrary: 'bootstrap4',
        format: DATE_FORMAT,
        value: today,
    });
    refreshMawaqit();
    $('#saved-toast').toast({ delay: 2000 });
});
