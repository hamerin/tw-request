$(document).ready(function () {
  function ajax_retrieve() {
    $.ajax({
      url: '/user_ajax/' + $('#userid').val(),
      dataType: 'json',
      type: 'GET',
      success: function (result) {
        $("#request-get").remove();
        $("#request-complete").remove();
        $('#form').after(result['html']);
      }
    });
  }

  function ajax_post() {
    $.ajax({
      url: '/user_ajax/' + $('#userid').val(),
      dataType: 'json',
      type: 'POST',
      data: $('#form > form').serializeObject(),
      success: function (result) {
        $("#request-get").remove();
        $("#request-complete").remove();
        $('#form').after(result['html']);
        $('#form > form')[0].reset();
      }
    })
  }

  ajax_retrieve();

  $('#submit_button').click(function () {
    ajax_post();
  });

  $('#search_button').click(function () {
    window.location.replace("/user/" + $("#search_id").val())
  });

  $('#search_id').keyup(function (e) {
    e.preventDefault();
    if(e.keyCode == 13) {
      window.location.replace("/user/" + $("#search_id").val())
    }
  });
});