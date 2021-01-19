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

async function fetchOneMawaqit(wilaya, date) {
    let params = new URLSearchParams({
        wilayas: wilaya,
        days: date,
    });
    let url = API_URL + "?" + params.toString();
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
    let date = $("#datepicker").val();
    let mawaqit = await fetchOneMawaqit(wilaya, date);
    updateMawaqit(mawaqit);
}


formatDate = (date) => date.toISOString().substring(0, 10);

$('#wilaya').change(refreshMawaqit);
$('#datepicker').change(refreshMawaqit);

$(function () {
    let today = formatDate(new Date());
    $("#datepicker").datepicker({
        uiLibrary: 'bootstrap4',
        format: DATE_FORMAT,
        value: today,
        change: function(e) {
            console.log('Change is fired');
        },
        select: function(e) {
            console.log('Selected a new value');
        }
    });
    refreshMawaqit();
});
