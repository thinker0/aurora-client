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
      --aurora-bg: rgba(0,0,0,0.02); --aurora-text-primary: #222;
      --aurora-navbar-hover: #333; --aurora-toggle-bg: rgba(0,0,0,0.1);
      --text: #000; --bg: #fff; --log-text: #000; --log-bg: #fff;
    }
    [data-theme="dark"] {
      --aurora-bg: #121212; --aurora-text-primary: #e0e0e0;
      --aurora-navbar-hover: #2a2a4a; --aurora-toggle-bg: rgba(255,255,255,0.1);
      --text: #e0e0e0; --bg: #1e1e2e; --log-text: #d4d4d4; --log-bg: #1e1e2e;
    }
    body { background-color: var(--aurora-bg); color: var(--aurora-text-primary); }
    [data-theme="dark"] body { background-color: #121212; color: #e0e0e0; }
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
    [data-theme="dark"] .invert {
      color: #000000;
      background: #FFFFFF;
    }
    .filename {
      color: var(--text);
      background-color: var(--bg);
    }
    .theme-toggle {
      background: var(--aurora-toggle-bg); border: 1px solid rgba(128,128,128,0.3);
      border-radius: 4px; color: var(--aurora-text-primary); cursor: pointer; font-size: 12px;
      line-height: 25px; margin: 4px 8px; padding: 0 10px; text-transform: uppercase;
    }
    .theme-toggle:hover { background: var(--aurora-navbar-hover); color: #fff; }
  </style>
  <script>
    (function() {
      var t = localStorage.getItem('aurora-theme') ||
        (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
      document.documentElement.setAttribute('data-theme', t);
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function(e) {
        if (!localStorage.getItem('aurora-theme')) {
          document.documentElement.setAttribute('data-theme', e.matches ? 'dark' : 'light');
          var b = document.getElementById('theme-btn');
          if (b) { b.textContent = e.matches ? 'Light' : 'Dark'; }
        }
      });
      window.toggleTheme = function() {
        var cur = document.documentElement.getAttribute('data-theme') || 'light';
        var nxt = cur === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', nxt);
        localStorage.setItem('aurora-theme', nxt);
        var b = document.getElementById('theme-btn');
        if (b) { b.textContent = nxt === 'dark' ? 'Light' : 'Dark'; }
      };
    })();
  </script>
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
  <div class="filename"> <strong> log </strong> ${logtype} <strong> ${download_link()} </strong> <button class="theme-toggle" id="theme-btn" onclick="toggleTheme()">Dark</button></div>
  <div style="position: absolute; left: 5px; top: 0px;">
    <p id="indicator" class="log invert"></p>
  </div>

  <div id="data" class="log" style="white-space:pre-wrap;"></div>
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

<script>
  document.addEventListener('DOMContentLoaded', function() {
    var b = document.getElementById('theme-btn');
    if (b) {
      b.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? 'Light' : 'Dark';
    }
  });
</script>
</html>
