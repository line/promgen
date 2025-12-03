/*
 * Copyright (c) 2021 LINE Corporation
 * These sources are released under the terms of the MIT license: see LICENSE
 */

function groupByLabel(items, label) {
  const groups = new Map();

  for (const item of items) {
    const key = item.labels[label];
    if (!key) {
      continue;
    }

    const group = groups.get(key);
    if (group) {
      group.push(item);
    } else {
      groups.set(key, [item]);
    }
  }

  return groups;
}

function update_page(data) {
  for (var key in data) {
    console.log("Replacing %s", key);
    var ele = $(data[key]);
    $(key).replaceWith(ele);
  }
}

function doesMatcherMatch(matcher, labelName, labelValue) {
  if (matcher.name !== labelName) {
    return false;
  }

  if (matcher.isRegex) {
    const regex = new RegExp("^(?:" + matcher.value + ")$");
    const matches = regex.test(labelValue);
    return matcher.isEqual ? matches : !matches;
  } else {
    return matcher.isEqual ?
      (matcher.value === labelValue) :
      (matcher.value !== labelValue);
  }
}

function getActiveSilences(items, labelName, labelValue) {
  const activeSilences = [];
  for (const item of items) {
    const matches = item.matchers.some(matcher =>
      doesMatcherMatch(matcher, labelName, labelValue)
    );
    if (matches) {
      activeSilences.push(item);
    }
  }
  return activeSilences;
}

// https://blog.bitsrc.io/debounce-understand-and-learn-how-to-use-this-essential-javascript-skill-9db0c9afbfc1
function debounce(func, delay = 250) {
  let timerId;
  return (...args) => {
    clearTimeout(timerId);
    timerId = setTimeout(() => {
      func.apply(this, args);
    }, delay);
  };
}

// Wait until DOM is loaded to add our extra listeners
document.addEventListener("DOMContentLoaded", function () {
  /*
    Copy to shortcut

    Example: <code data-copyto="#id_duration">30s</code>
  */
  document.querySelectorAll("[data-copyto]").forEach(srcElement => {
    srcElement.style.cursor = "pointer";
    srcElement.addEventListener("click", e => {
      const dstElement = document.querySelector(srcElement.dataset.copyto);
      dstElement.value = srcElement.innerText;
    });
  });

  /*
  Filter Element

  Example: <input data-filter="div.auto-grid div">
  */
  document.querySelectorAll("[data-filter]").forEach(srcElement => {
    const filterTarget = document.querySelectorAll(srcElement.dataset.filter);

    srcElement.addEventListener(
      "input",
      debounce(e => {
        const search = srcElement.value.toUpperCase();
        console.debug("Searching for", search);
        for (const child of filterTarget) {
          const txt = child.innerText.toUpperCase();
          child.style.display = txt.indexOf(search) > -1 ? "block" : "none";
        }
      })
    );
  });
});

function initSelect2() {
  const selectors = ["username", "owner", "group", "user_to_merge_from", "user_to_merge_into"]
    .map(name => `select[name="${name}"]`)
    .join(",");
  $(selectors).select2({
    placeholder: "Select an option",
    width: "25%",
  });
  $('select[name="users"]').select2({
    multiple: "multiple",
    placeholder: "Select users",
  });
}

// Activate a tab based on the hash value of the URL
// For example, if the URL is `http://example.com#tab2`, it will activate the tab with id `tab2`.
function activateTabFromHash() {
  const hash = window.location.hash;
  if (hash && $(hash).length) {
    // Remove active class from all tabs and tab content
    $(".nav-tabs li").removeClass("active");
    $(".tab-pane:not(.perm-tab-pane)").removeClass("active");

    // Add active class to tab and tab content that matches the hash
    $('a[href="' + hash + '"]').parent().addClass("active");
    $(hash).addClass("active");

    // The Select2 constructor relies on being able to read the dimensions of the input element,
    // which cannot be done when it's not part of the DOM yet, or hidden.
    // To fix this, instantiate the Select2 again when the tab becomes visible.
    // Ref: https://stackoverflow.com/questions/55277454/select2-not-working-inside-a-bootstrap-tab
    initSelect2();
  }
}

$(document).ready(function() {
  $('[data-toggle="popover"]').popover();
  $('[data-toggle="tooltip"]').tooltip();

  $('[data-source]').click(function() {
    var btn = $(this);
    var query = btn.data('source') === 'self' ? btn.text() : $(btn.data('source')).val();

    $(btn.data('target')).html('Loading...').show();
    btn.data('query', query);
    console.log("Testing Query: %s", query);
    $.post(btn.data('href'), btn.data()).done(update_page);
  }).css('cursor', 'pointer');

  $('[data-toggle="toggle"]').bootstrapSwitch();
  $('[data-toggle="toggle"][data-action]').on('switchChange.bootstrapSwitch', function(event, state) {
    if (window.confirm("Are you sure?")) {
      $.post(this.dataset.action, this.dataset).done(function(data){
        // Ideally we would directly update things that need to be updated
        // but a page redraw is a bit easier since that also allows us to
        // update our page messages
        window.location = data.redirect;
        if (data.redirect.includes('#')) {
          // If the redirect contains a hash, the browser may not reload the page
          // so we need to force a reload. Otherwise this code won't be reached.
          window.location.reload();
        }
      });
    } else {
      // If we click the cancel button, then we restore the old state and
      // use the third parameter to skip re-firing the change event
      $(this).bootstrapSwitch('state', !state, true);
    }
  });

  // Activate tab based on hash on page load
  activateTabFromHash();

  // Update the hash when a tab is clicked
  $('.nav-tabs a').on('click', function(e) {
      window.location.hash = this.hash;
  });

  // Activate tab based on hash changed by back/forward navigation
  $(window).on('hashchange', function() {
      activateTabFromHash();
  });

  $('input[type="radio"][name="perm-type"]').change(function () {
    const target = $(this).data("target");
    $(".perm-tab-pane").removeClass("active in");
    $(target + "-label").addClass("active in");
    $(target + "-select").addClass("active in");
    initSelect2();
  });

  // Initialize Select2 for the select elements
  initSelect2();
});
