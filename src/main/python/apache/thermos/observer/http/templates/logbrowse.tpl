<!--
 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
 -->

 <%def name="download_link()">
  <a href='/download/${task_id}/${filename}'><font size=1>download</font></a>
</%def>

<html>

<head>
  <meta charset="utf-8">
  <title></title>

  <style type="text/css">
    :root {
      --text: #000;
      --bg: #fff;
      --log-text: #000;
      --log-bg: #fff;
    }
    .log {
      font-family: "Inconsolata", "Monaco", "Courier New", "Courier";
      line-height:14px;
      font-size: 12px;
      color: var(--log-text);
      background-color: var(--log-bg);
    }

    .invert {
      color: #FFFFFF;
      text-decoration: none;
      background: #000000;
    }
    .filename {
      color: var(--text);
      background-color: var(--bg);
    }
    @media (prefers-color-scheme: dark) {
      :root {
        --text: #fff;
        --bg: #000;
        --log-text: #333;
        --log-bg: #fff;
      }
      .invert {
        color: #000000;
        background: #FFFFFF;
      }
    }
  </style>
  <link rel="icon" href="/assets/favicon.ico">
</head>

<link rel="stylesheet"
      type="text/css"
      href="/assets/bootstrap.css"/>
<style type="text/css">
div.tight
{
  height:100%;
  overflow:scroll;
}
</style>
<link rel="stylesheet" type="text/css" href="/assets/navbar.css"/>
<title>log browser ${task_id}</title>
<body>
  <div class="filename"> <strong> log </strong> ${logtype} <strong> ${download_link()} </strong> </div>
  <div style="position: absolute; left: 5px; top: 0px;">
    <p id="indicator" class="log invert"></p>
  </div>

  <div id="data" class="log" style="white-space:pre-wrap; background-color:#EEEEEE;"></div>
</body>

<script src="/assets/jquery.js"></script>
<script src="/assets/jquery.pailer.js"></script>

<script>
  function resize() {
    var margin_left = parseInt($('body').css('margin-left'));
    var margin_top = parseInt($('body').css('margin-top'));
    var margin_bottom = parseInt($('body').css('margin-bottom'));
    $('#data').width($(window).width() - margin_left);
    $('#data').height($(window).height() - margin_top - margin_bottom);
  }

  $(window).resize(resize);

  $(document).ready(function() {
    resize();

    $('#data').pailer({
      'read': function(options) {
        var settings = $.extend({
          'offset': -1,
          'length': -1
        }, options);

        var url = "/logdata/${task_id}/${process}/${run}/${logtype}"
          + '?offset=' + settings.offset
          + '&length=' + settings.length;
        return $.getJSON(url);
      },
      'indicator': $('#indicator')
    });
  });
</script>
</html>
