/*
# Copyright (c) 2017 LINE Corporation
# These sources are released under the terms of the MIT license: see LICENSE
*/

function silence_tag() {
  var labels = this.dataset;
  var form = $('#silence-form');
  for (var label in labels) {
    var value = labels[label];
    console.debug('Adding %s %s', label, value);

    form.find('a.' + label).remove();

    input = $('<input type="hidden" class="form-control" />');
    input.val(value).attr('name', 'label.' + label);

    span = $('<a class="label label-warning"></a>').addClass(label);
    span.attr('onclick', 'this.parentNode.removeChild(this); return false;');
    span.text(label + ':' + value);
    span.append(input);
    span.append($('<span class="glyphicon glyphicon-remove" aria-hidden="true"></span>'));

    form.find('div.labels').append(span);
  }

  form.show();
}

function update_page(data) {
  for (var key in data) {
    console.log("Replacing %s", key);
    var ele = $(data[key]);
    ele.find("a.promgen-silence").click(silence_tag);
    $(key).replaceWith(ele);
  }
}


function label(key, value) {
  var tmpl = document.querySelector('template.label');
  var ele = document.importNode(tmpl.content, true);
  var a = ele.querySelector('a');
  a.text = key + ':' + value;
  a.dataset[key] = value;
  return ele;
}

function row(href, text) {
  var tmpl = document.querySelector('template.alertrow');
  var ele = document.importNode(tmpl.content, true);
  var a = ele.querySelector('td a');
  a.href = href;
  a.text = text;
  return ele;
}

function annotation(dt, dd) {
  var tmpl = document.querySelector('template.annotation');
  var ele = document.importNode(tmpl.content, true);
  ele.querySelector('dt').textContent = dt;
  ele.querySelector('dd').innerHTML = dd;
  return ele;
}

$(document).ready(function() {
  $("a.promgen-silence").click(silence_tag);
  $('[data-toggle="popover"]').popover();
  $('[data-toggle="tooltip"]').tooltip();

  $.ajax("/ajax/alert").done(function(alerts){
    var btn = document.getElementById('alert-load');
    var panel = document.getElementById('alert-all');

    for (var alert_id in alerts) {
      var alert = alerts[alert_id];
      var r = row(alert.generatorURL, alert.startsAt);
      var labels = annotation('labels', '');
      for (var k in alert.labels) {
        var l = label(k, alert.labels[k]);
        labels.querySelector('dd').appendChild(l);
      }
      r.querySelector('dl').appendChild(labels);

      for (var k in alert.annotations) {
        var a = annotation(k, alert.annotations[k]);
        r.querySelector('dl').appendChild(a);
      }

      for (var k in alert.labels) {
        var sel = '.promgen-alert[data-'+k+'^="'+alert.labels[k].split(':')[0]+'"]';
        console.debug('Searching for', sel);
        var target = document.querySelector('.promgen-alert[data-'+k+'^="'+alert.labels[k].split(':')[0]+'"]');
        if (target) {
          target.querySelector('table').appendChild(r.cloneNode(true));
          target.style.display = 'block';
        }
      }
      panel.querySelector('table').appendChild(r);
    }

    if (alerts.length > 0) {
      btn.classList.remove('btn-default');
      btn.classList.add('btn-danger');
      btn.text = 'Alerts ' + alerts.length;
    }
    document.querySelectorAll('a.promgen-silence').forEach(function(ele){
      ele.onclick = silence_tag;
    });
  });

  $.post("/ajax/silence", {
    'referer': window.location.toString()
  }).done(update_page);

  $('[data-source]').click(function() {
    var btn = $(this);
    var query = btn.data('source') === 'self' ? btn.text() : $(btn.data('source')).val();

    $(btn.data('target')).html('Loading...').show();
    btn.data('query', query);
    console.log("Testing Query: %s", query);
    $.post(btn.data('href'), btn.data()).done(update_page);
  }).css('cursor', 'pointer');

  $('[data-form]').click(function() {
    var form = document.querySelector(this.dataset.form);
    $(this.dataset.target).html('Loading...').show();
    // TODO: Make this more general ?
    $.post(this.dataset.href, {
      'target': this.dataset.target,
      'job': form.elements.job.value,
      'port': form.elements.port.value,
      'path': form.elements.path.value,
      'csrfmiddlewaretoken': form.elements.csrfmiddlewaretoken.value
    }).done(update_page);
  }).css('cursor', 'pointer');

  $('[data-copyto]').click(function(){
    var ele = $(this);
    $(ele.data('copyto')).val(ele.text())
  }).css('cursor', 'pointer');

  $('[data-toggle="toggle"]').bootstrapSwitch();
  $('[data-toggle="toggle"][data-action]').on('switchChange.bootstrapSwitch', function(event, state) {
    if (window.confirm("Are you sure?")) {
      $.post(this.dataset.action, this.dataset).done(function(data){
        // Ideally we would directly update things that need to be updated
        // but a page redraw is a bit easier since that also allows us to
        // update our page messages
        window.location = data.redirect
      });
    } else {
      // If we click the cancel button, then we restore the old state and
      // use the third parameter to skip re-firing the change event
      $(this).bootstrapSwitch('state', !state, true);
    }
  });

  $("select[data-ajax]").each(function(index) {
    var ele = $(this);
    var tgt = $(ele.data('target'));

    $.get(ele.data('ajax')).done(function(data){
      data.data.forEach(function(item){
        var option = $('<option>');
        option.html(item);
        option.val(item);
        option.appendTo(ele);
      });

      tgt.typeahead({
        source: data.data,
        items: "all",
        updater: function(item) {
          return item + ele.data("append")
        }
      })
    });

    ele.change(function(){
      var replacement = ele.val() ? ele.val() + ele.data("append") : "";
      tgt.selection("replace", {text: replacement, mode: "before"});
      tgt.focus();
    });

  });

  $('[data-filter]').change(function(){
    var search = this.value.toUpperCase();
    $(this.dataset.filter).each(function(i, ele){
      var txt = $(this).text().toUpperCase();
      ele.style.display = txt.indexOf(search) > -1 ? "" : "none"
    })
  });

  $('.silence_start').datetimepicker({
    format: 'YYYY-MM-DD HH:mm'
  });
  $('.silence_end').datetimepicker({
    format: 'YYYY-MM-DD HH:mm',
    useCurrent: false //Important! See issue #1075
  });
  $(".silence_start").on("dp.change", function(e) {
    $('.silence_end').data("DateTimePicker").minDate(e.date);
  });
  $(".silence_end").on("dp.change", function(e) {
    $('.silence_start').data("DateTimePicker").maxDate(e.date);
  });
});

$('#silence-form-close').click( function() {
  $('#silence-form').hide();
});
