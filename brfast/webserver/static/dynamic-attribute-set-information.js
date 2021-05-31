/**
 * JS script to collect asynchronously the information about an attribute set.
 */

// ##### Variables and parameters

// The origin of the website and the URL for the /get-trace GET request
const BRFAST_ORIGIN = window.location.origin;
const ENTROPY_RESULT_URL = BRFAST_ORIGIN + '/attribute-set-entropy';
const UNICITY_RESULT_URL = BRFAST_ORIGIN + '/attribute-set-unicity';


// ##### Functions

/**
 * Get the entropy results.
 */
function getEntropyResults() {
  // Build and execute the GET request
  let xhr = new XMLHttpRequest();
  const url = ENTROPY_RESULT_URL + '/' + $('#attribute-set-id').text();
  console.log('Getting ' + url);
  xhr.open('GET', url, true); // true for asynchronous request

  xhr.onload = function (e) {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        setEntropyResults(xhr.responseText);
        getUnicityResults();
      } else {
        console.error(xhr.statusText);
      }
    }
  };
  xhr.onerror = function (e) {
    console.error(xhr.statusText);
  };
  xhr.send(null);
}


/**
 * Get the unicity results.
 */
function getUnicityResults() {
  // Build and execute the GET request
  let xhr = new XMLHttpRequest();
  const url = UNICITY_RESULT_URL + '/' + $('#attribute-set-id').text();
  console.log('Getting ' + url);
  xhr.open('GET', url, true); // true for asynchronous request

  xhr.onload = function (e) {
    if (xhr.readyState === 4) {
      if (xhr.status === 200) {
        setUnicityResults(xhr.responseText);
      } else {
        console.error(xhr.statusText);
      }
    }
  };
  xhr.onerror = function (e) {
    console.error(xhr.statusText);
  };
  xhr.send(null);
}


/**
 * Set the entropy results.
 */
function setEntropyResults(jsonResponse) {
  // Parse the response as a JSON
  const entropyResults = JSON.parse(jsonResponse);

  // Set the different values from this response
  $('#attribute-set-entropy').text(entropyResults.entropy.toFixed(FLOAT_PRECISION));
  $('#attribute-set-normalized-entropy').text(entropyResults.normalized_entropy.toFixed(FLOAT_PRECISION));
  $('#attribute-set-maximum-entropy').text(entropyResults.maximum_entropy.toFixed(FLOAT_PRECISION));
}


/**
 * Set the unicity results.
 */
function setUnicityResults(jsonResponse) {
  // Parse the response as a JSON
  const unicityResults = JSON.parse(jsonResponse);

  // Set the different values from this response
  $('#attribute-set-unicity-rate').text(unicityResults.unicity_rate.toFixed(FLOAT_PRECISION));
  $('#attribute-set-unique-fingerprints').text(unicityResults.unique_fingerprints);
  $('#attribute-set-total-browsers').text(unicityResults.total_browsers);
}


// ##### Main execution of this script
getEntropyResults();

// NOTE Update: We will now get the unicity result after getting the entropy
//      result in a sequential manner to let the preprocessing of the dataset
//      take place.
// getUnicityResults();
