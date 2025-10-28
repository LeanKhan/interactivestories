/* Copyright 2014 Mozilla Foundation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

if (!pdfjsLib.getDocument || !pdfjsViewer.PDFSinglePageViewer) {
  // eslint-disable-next-line no-alert
  alert("Please build the pdfjs-dist library using\n  `gulp dist-install`");
}

// The workerSrc property shall be specified.
//
pdfjsLib.GlobalWorkerOptions.workerSrc =
  "/static/pdfjs-5.4.54-dist/build/pdf.worker.mjs";

// Some PDFs need external cmaps.
//
const CMAP_URL = "/static/pdfjs-5.4.54-dist/web/cmaps/";
const CMAP_PACKED = true;

// To test the AcroForm and/or scripting functionality, try e.g. this file:
// "../../test/pdfs/160F-2019.pdf"

const ENABLE_XFA = true;
const SEARCH_FOR = ""; // try "Mozilla";

const SANDBOX_BUNDLE_SRC = new URL(
  "/static/pdfjs-5.4.54-dist/build/pdf.sandbox.mjs",
  window.location
);

const container = document.getElementById("viewerContainer");

const eventBus = new pdfjsViewer.EventBus();

// (Optionally) enable hyperlinks within PDF files.
const pdfLinkService = new pdfjsViewer.PDFLinkService({
  eventBus,
});

// (Optionally) enable find controller.
const pdfFindController = new pdfjsViewer.PDFFindController({
  eventBus,
  linkService: pdfLinkService,
});

// (Optionally) enable scripting support.
const pdfScriptingManager = new pdfjsViewer.PDFScriptingManager({
  eventBus,
  sandboxBundleSrc: SANDBOX_BUNDLE_SRC,
});

const pdfSinglePageViewer = new pdfjsViewer.PDFSinglePageViewer({
  container,
  eventBus,
  linkService: pdfLinkService,
  findController: pdfFindController,
  scriptingManager: pdfScriptingManager,
});
pdfLinkService.setViewer(pdfSinglePageViewer);
pdfScriptingManager.setViewer(pdfSinglePageViewer);

// Make pdfSinglePageViewer globally accessible for controls
window.pdfSinglePageViewer = pdfSinglePageViewer;

// Helper function to detect mobile devices and portrait orientation
function isMobileDevice() {
  return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)
    || window.innerWidth <= 768;
}

function isPortraitMode() {
  return window.innerHeight > window.innerWidth;
}

function getOptimalScale() {
  const isMobile = isMobileDevice();
  const isPortrait = isPortraitMode();

  if (isMobile && isPortrait) {
    // For mobile portrait, use page-width to fit PDF width to screen
    return "page-width";
  } else if (isMobile && !isPortrait) {
    // For mobile landscape, use page-fit to fit entire page
    return "page-fit";
  } else {
    // For desktop, use fixed scale
    return "0.7";
  }
}

eventBus.on("pagesinit", function () {
  // Set scale based on device and orientation
  pdfSinglePageViewer.currentScaleValue = getOptimalScale();

  // We can try searching for things.
  if (SEARCH_FOR) {
    eventBus.dispatch("find", { type: "", query: SEARCH_FOR });
  }
});

// Listen for orientation changes and window resizes to adjust scale
window.addEventListener("orientationchange", function() {
  setTimeout(function() {
    pdfSinglePageViewer.currentScaleValue = getOptimalScale();
  }, 100);
});

window.addEventListener("resize", function() {
  // Debounce resize events
  clearTimeout(window.resizeTimeout);
  window.resizeTimeout = setTimeout(function() {
    pdfSinglePageViewer.currentScaleValue = getOptimalScale();
  }, 250);
});

// Loading document.
  console.log('Default URL ', DEFAULT_URL)
const loadingTask = pdfjsLib.getDocument({
  url: DEFAULT_URL,
  cMapUrl: CMAP_URL,
  cMapPacked: CMAP_PACKED,
  enableXfa: ENABLE_XFA,
});

const pdfDocument = await loadingTask.promise;
// Document loaded, specifying document for the viewer and
// the (optional) linkService.
pdfSinglePageViewer.setDocument(pdfDocument);

pdfLinkService.setDocument(pdfDocument, null);