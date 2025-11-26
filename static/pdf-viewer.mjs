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
  } else {
    // For mobile landscape and desktop, use page-fit to ensure PDF fits within screen
    return "page-fit";
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

// Animation for linkAnnotation on first page
let animationTimeout = null;
let animationInterval = null;
let linkAnnotationClicked = false;

function startLinkAnnotationAnimation() {
  // Wait for the page to be rendered
  setTimeout(() => {
    const linkAnnotation = document.querySelector('.page[data-page-number="1"] .linkAnnotation > a');
console.log('Link Annotation => ', linkAnnotation);
    if (!linkAnnotation) {
      return;
    }

    // Add click listener to stop animation
    linkAnnotation.addEventListener('click', () => {
      linkAnnotationClicked = true;
      if (animationTimeout) {
        clearTimeout(animationTimeout);
      }
      if (animationInterval) {
        clearInterval(animationInterval);
      }
      linkAnnotation.style.animation = 'none';
    }, { once: true });

    // Start animation after 30 seconds if not clicked
    animationTimeout = setTimeout(() => {
      if (!linkAnnotationClicked) {
        console.log('Not clicked! Applying animation')
        // Add CSS animation
        const style = document.createElement('style');
        style.textContent = `
          @keyframes pulseScale {
            0%, 100% {
              transform: scale(1);
              scale: 200% 1;
            }
            50% {
              transform: scale(1.1);
              scale: 100% 1;
            }
          }
        `;
        document.head.appendChild(style);

        linkAnnotation.style.animation = 'pulseScale 1s ease-in-out infinite';
      }
    }, 10000); // 30 seconds
  }, 500);
}

// Start animation when pages are initialized
eventBus.on('pagerendered', async function(evt) {

  console.log('Evet => ', evt)
//   const annotations = await page.getAnnotations();

// for (const a of annotations) {
//   if (a.subtype === 'Link' && a.url) {
//     console.log('Link found:', a);
//   }
// }

  console.log('Page Rendered!')
  if (evt.pageNumber === 1 && !animationTimeout) {
    startLinkAnnotationAnimation();
  }
});