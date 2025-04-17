/* UPDATE THESE VALUES TO MATCH YOUR SETUP */

const PROCESSING_STATS_API_URL = "http://20.55.37.190/processing/stats"
const ANALYZER_API_URL = {
    stats: "http://20.55.37.190/analyzer/stats",
    flight: "http://20.55.37.190/analyzer/flights/schedule/random",
    passenger: "http://20.55.37.190/analyzer/passenger/checkin/random"
}

const CONSISTENCY_API_URL = {
    update: "http://20.55.37.190/consistency_check/update",
    checks: "http://20.55.37.190/consistency_check/checks"
}

// This function fetches and updates the general statistics
const makeReq = (url, cb) => {
    fetch(url)
        .then(res => res.json())
        .then((result) => {
            console.log("Received data: ", result)
            cb(result);
        }).catch((error) => {
            updateErrorMessages(error.message)
        })
}

const updateCodeDiv = (result, elemId) => document.getElementById(elemId).innerText = JSON.stringify(result)

const getLocaleDateStr = () => (new Date()).toLocaleString()

const getStats = () => {
    document.getElementById("last-updated-value").innerText = getLocaleDateStr()
    
    makeReq(PROCESSING_STATS_API_URL, (result) => updateCodeDiv(result, "processing-stats"))
    makeReq(ANALYZER_API_URL.stats, (result) => updateCodeDiv(result, "analyzer-stats"))
    makeReq(ANALYZER_API_URL.flight, (result) => updateCodeDiv(result, "event-flight"))
    makeReq(ANALYZER_API_URL.passenger, (result) => updateCodeDiv(result, "event-passenger"))
}

const runConsistencyCheck = (event) => {
    event.preventDefault()
    // POST to run the consistency check update
    fetch(CONSISTENCY_API_URL.update, { method: "POST" })
        .then(res => res.json())
        .then((result) => {
            console.log("Consistency check update result:", result)
            // After update, retrieve the latest consistency check results
            return fetch(CONSISTENCY_API_URL.checks)
        })
        .then(res => res.json())
        .then((result) => {
            updateCodeDiv(result, "consistency-stats")
        })
        .catch((error) => {
            updateErrorMessages(error.message)
        })
}

const updateErrorMessages = (message) => {
    const id = Date.now()
    console.log("Creation", id)
    msg = document.createElement("div")
    msg.id = `error-${id}`
    msg.innerHTML = `<p>Something happened at ${getLocaleDateStr()}!</p><code>${message}</code>`
    document.getElementById("messages").style.display = "block"
    document.getElementById("messages").prepend(msg)
    setTimeout(() => {
        const elem = document.getElementById(`error-${id}`)
        if (elem) { elem.remove() }
    }, 7000)
}

const setup = () => {
    getStats()
    setInterval(() => getStats(), 4000) // Update every 4 seconds
    document.getElementById("consistency-form").addEventListener("submit", runConsistencyCheck)
}

document.addEventListener('DOMContentLoaded', setup)