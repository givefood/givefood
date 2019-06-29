$(function(){
  $(window).on("swipeleft", function(e){
    window.location = $("link[rel='next']").attr("href")
  })
  $(window).on("swiperight", function(e){
    window.location = $("link[rel='prev']").attr("href")
  })
})
