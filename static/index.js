const API_URL = "/api/v1/mawaqit";
const SALAWAT_NAMES = {
    "fajr": "الفجر",
    "chorok": "الشروق",
    "dhohr": "الظهر",
    "asr": "العصر",
    "maghrib": "المغرب",
    "icha": "العشاء"
};

async function fetchMawaqit(wilaya) {
    let url = API_URL + "?wilayas=" + wilaya;
    // let options = {'mode': 'no-cors'};

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
    let mawaqit = await fetchMawaqit(wilaya);
    updateMawaqit(mawaqit);
}

$('#wilaya').change(refreshMawaqit);

$(function () {
    refreshMawaqit();
});
