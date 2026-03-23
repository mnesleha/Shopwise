/**
 * Mutual-exclusion for DefaultRadioWidget radios inside Django admin inlines.
 *
 * Django gives each inline row its own unique field name
 * (e.g. "supplieraddress_set-0-is_default_for_orders"), so the browser
 * cannot group them by the HTML `name` attribute as it would for normal
 * radio buttons.  This script implements the grouping in JavaScript using
 * the `data-default-radio` attribute emitted by DefaultRadioWidget.
 *
 * When any radio is checked, every other radio in the same group is
 * unchecked.  Works for rows present on page load and for rows added
 * dynamically via Django's "Add another" inline link.
 */
(function () {
  "use strict";

  document.addEventListener("change", function (e) {
    var radio = e.target;
    if (radio.type !== "radio" || !radio.classList.contains("default-radio")) {
      return;
    }
    var group = radio.dataset.defaultRadio;
    if (!group) return;

    document
      .querySelectorAll(
        'input.default-radio[type="radio"][data-default-radio="' + group + '"]',
      )
      .forEach(function (r) {
        if (r !== radio) {
          r.checked = false;
        }
      });
  });
})();
