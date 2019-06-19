$(document).ready(function () {
  function ajax_retrieve(callback) {
    $.ajax({
      url: '/me_ajax',
      dataType: 'json',
      type: 'GET',
      success: function (result) {
        $('#main').html(result['html']);
        callback();
      }
    });
  }

  function ajax_post() {
    $.ajax({
      url: '/me_ajax',
      dataType: 'json',
      type: 'POST',
      data: $('#form > form').serializeObject(),
      success: function (result) {
        $('#main').html(result['html']);
        $('#form > form')[0].reset();
      }
    })
  }

  ajax_retrieve(() => {
    $('#submit_button').click(function () {
      ajax_post();
    });

    $('#discard').click(function () {
      $('#isSharing').closest("div").children('label').removeClass("disabled");
      $('#isSharing').removeAttr("disabled");
      $('#isSharing').prop("checked", true);
    });

    $('#accept').click(function () {
      $('#isSharing').closest("div").children('label').addClass("disabled");
      $('#isSharing').attr("disabled", "");
      $('#isSharing').prop("checked", false);
    });

    $('#search_button').click(function () {
      window.location.replace("/user/" + $("#search_id").val())
    });
  });
});