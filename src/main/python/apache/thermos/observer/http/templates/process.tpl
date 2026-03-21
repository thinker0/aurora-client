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

 <%doc>
Template arguments:
  task_id
  process {
    cpu:/ram: (optional)
    cmdline:
    name:
  }

  runs = {
   number: {
     start_time: (optional)
     stop_time: (optional)
     state:
   }
  }

  --
  for each run:
     run | state | started | finished | stdout | stderr
</%doc>

<%!
import socket
import time
from xml.sax.saxutils import escape

def pretty_time(seconds=time.time()):
  return time.strftime('%m/%d %H:%M:%S', time.gmtime(seconds))
%>

<html>
<title>thermos(${socket.gethostname()})</title>

<link rel="stylesheet"
      type="text/css"
      href="/assets/bootstrap.css"/>
<link rel="stylesheet" type="text/css" href="/assets/navbar.css"/>
<style>
  :root {
    --aurora-bg: rgba(0,0,0,0.02); --aurora-surface: #fff;
    --aurora-surface-alt: #fafafa; --aurora-contrast: #222;
    --aurora-grid: #eee; --aurora-text-primary: #222;
    --aurora-text-secondary: #999; --aurora-border: #d7e2ec;
    --aurora-navbar-hover: #444; --aurora-toggle-bg: rgba(255,255,255,0.15);
  }
  [data-theme="dark"] {
    --aurora-bg: #121212; --aurora-surface: #1e1e2e;
    --aurora-surface-alt: #252535; --aurora-contrast: #e0e0e0;
    --aurora-grid: #2a2a3a; --aurora-text-primary: #e0e0e0;
    --aurora-text-secondary: #aaa; --aurora-border: #3a3a5a;
    --aurora-navbar-hover: #2a2a4a; --aurora-toggle-bg: rgba(255,255,255,0.1);
  }
  body { background-color: var(--aurora-bg); color: var(--aurora-text-primary); }
  [data-theme="dark"] table { color: var(--aurora-text-primary); }
  [data-theme="dark"] table th,
  [data-theme="dark"] table td { border-color: var(--aurora-grid); }
  [data-theme="dark"] tr:nth-child(odd) { background-color: var(--aurora-surface-alt); }
  [data-theme="dark"] .well { background-color: var(--aurora-surface-alt); border-color: var(--aurora-border); }
  .theme-toggle {
    background: var(--aurora-toggle-bg); border: 1px solid rgba(255,255,255,0.3);
    border-radius: 4px; color: #fff; cursor: pointer; font-size: 12px;
    line-height: 25px; margin: 12px 8px; padding: 0 10px; text-transform: uppercase;
  }
  .theme-toggle:hover { background: var(--aurora-navbar-hover); }
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
<body>
<nav class="navbar">
  <div class="container">
    <div class="navbar-header">
      <a class="navbar-brand" href="${scheduler_web_url}/scheduler"><img alt="Brand" src="${scheduler_web_url}/assets/images/aurora_logo_white.png"></a>
    </div>
    <ul class="nav navbar-nav navbar-right">
      <li><a href="${scheduler_web_url}/updates">updates</a></li>
      <li>
        <button class="theme-toggle" id="theme-btn" onclick="toggleTheme()">Dark</button>
      </li>
    </ul>
  </div>
</nav>


<div class="container">
  <div class="row">
    <div class="span6" id="leftBar">
      <dl>
        <dt> process </dt>
          <dd> <strong> parent task </strong> <a href="/task/${task_id}">${task_id}</a> </dd>
          <dd> <strong> process name </strong> ${process["name"]} </dd>
          <dd> <strong> status </strong> ${process["status"]} </dd>
      </dl>
    </div>

    <div class="span6" id="rightBar">
      <dl>
        <dt> resources </dt>
          <dd> <strong> cpu </strong> ${'%.3f' % process["cpu"] if "cpu" in process else "N/A"} </dd>
          <dd> <strong> ram </strong> ${'%.1fMB' % (process["ram"] / 1024. / 1024.) if "ram" in process else "N/A"} </dd>
          <dd> <strong> total user </strong> ${'%.1fs' % process["user"] if "user" in process else "N/A"} </dd>
          <dd> <strong> total sys </strong> ${'%.1fs' % process["system"] if "system" in process else "N/A"} </dd>
          <dd> <strong> threads </strong> ${process["threads"] if "threads" in process else "N/A"} </dd>
      </dl>
    </div>
  </div>


  <strong> cmdline </strong><br>
  <div class="container">
<pre>
${escape(process["cmdline"])}
</pre>
  </div><br><br>


  <strong> runs </strong>
  <div class="container">
     <table class="table table-bordered table-condensed table-striped" style="empty-cells:show;">
     <thead>
       <tr>
         <th colspan=3> </th>
         <th colspan=2> time </th>
         <th colspan=2> logs </th>
       </tr>

       <tr>
         <th> run </th> <th> status </th> <th>return code</th>
         <th> started </th> <th> finished </th>
         <th> stdout </th> <th> stderr </th>
       </tr>
      </thead>
      <tbody>

      % for run, process_dict in sorted(runs.items(), reverse=True):
       <tr>
         <td> ${run} </td>
         <td> ${process_dict["state"]} </td>
         <td> ${process_dict["return_code"] if "return_code" in process_dict else ""} </td>
         <td> ${pretty_time(process_dict["start_time"]) if "start_time" in process_dict else ""} </td>
         <td> ${pretty_time(process_dict["stop_time"]) if "stop_time" in process_dict else ""} </td>
         <td> <a href="/logs/${task_id}/${process["name"]}/${run}/stdout">stdout</a> </td>
         <td> <a href="/logs/${task_id}/${process["name"]}/${run}/stderr">stderr</a> </td>
       </tr>
      % endfor
     </tbody>
     </table>
  </div>

</div>

<script>
  document.addEventListener('DOMContentLoaded', function() {
    var b = document.getElementById('theme-btn');
    if (b) {
      b.textContent = document.documentElement.getAttribute('data-theme') === 'dark' ? 'Light' : 'Dark';
    }
  });
</script>

</body>
</html>
