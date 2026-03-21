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
   chroot
   path
   dirs
   files
   scheduler_web_url
</%doc>


<%!
  import os

  from datetime import datetime
  import grp
  import os
  import pwd
  import stat
  import sys

  NOW = datetime.now()

  def format_mode(sres):
    mode = sres.st_mode

    root = (mode & 0o700) >> 6
    group = (mode & 0o070) >> 3
    user = (mode & 0o7)

    def stat_type(md):
      if stat.S_ISDIR(md):
        return 'd'
      elif stat.S_ISSOCK(md):
        return 's'
      else:
        return '-'

    def triple(md):
      return '%c%c%c' % (
        'r' if md & 0b100 else '-',
        'w' if md & 0b010 else '-',
        'x' if md & 0b001 else '-')

    return ''.join([stat_type(mode), triple(root), triple(group), triple(user)])

  def format_mtime(mtime):
    dt = datetime.fromtimestamp(mtime)
    return '%s %2d %5s' % (dt.strftime('%b'), dt.day,
      dt.year if dt.year != NOW.year else dt.strftime('%H:%M'))

  def format_prefix(filename, sres):
    try:
      pwent = pwd.getpwuid(sres.st_uid)
      user = pwent.pw_name
    except KeyError:
      user = sres.st_uid

    try:
      grent = grp.getgrgid(sres.st_gid)
      group = grent.gr_name
    except KeyError:
      group = sres.st_gid

    return '%s %3d %10s %10s %10d %s' % (
      format_mode(sres),
      sres.st_nlink,
      user,
      group,
      sres.st_size,
      format_mtime(sres.st_mtime),
    )
%>

<%def name="download_link(filename)"><a href='/download/${task_id}/${os.path.join(path, filename)}'><font size=1>dl</font></a></%def>
<%def name="directory_link(dirname)"><a href='/browse/${task_id}/${os.path.join(path, dirname)}'>${dirname}</a></%def>
<%def name="file_link(filename)"><a href='/file/${task_id}/${os.path.join(path, filename)}'>${filename}</a></%def>

<html>

<link rel="stylesheet"
      type="text/css"
      href="/assets/bootstrap.css"/>
<style type="text/css">
div.tight
{
  height:85%;
  overflow:auto;
}
</style>
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
  [data-theme="dark"] body { background-color: #121212; color: #e0e0e0; }
  [data-theme="dark"] table { color: var(--aurora-text-primary); background-color: var(--aurora-surface); }
  [data-theme="dark"] table th,
  [data-theme="dark"] table td { border-color: var(--aurora-grid); background-color: var(--aurora-surface); }
  [data-theme="dark"] .table-striped > tbody > tr:nth-of-type(odd) > td,
  [data-theme="dark"] .table-striped > tbody > tr:nth-of-type(odd) > th { background-color: var(--aurora-surface-alt); }
  [data-theme="dark"] .well { background-color: var(--aurora-surface-alt); border-color: var(--aurora-border); }
  [data-theme="dark"] pre { background-color: var(--aurora-surface); border-color: var(--aurora-border); color: var(--aurora-text-primary); }
  [data-theme="dark"] a { color: #6eb3f5; }
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
<title>path browser for ${task_id}</title>


% if chroot is not None:
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
  <div class="span6">
    <strong> task id </strong> ${task_id}
  </div>
  <div class="span6">
    <strong> path </strong> ${path}
  </div>
  <div class="span12 tight">
    <pre>

% if path != ".":
  <%
     listing = ['..'] + os.listdir(os.path.join(chroot, path))
  %>\
% else:
  <%
     listing = os.listdir(os.path.join(chroot, path))
  %>\
% endif

<% listing.sort() %>

% for fn in listing:
<%
  try:
    sres = os.stat(os.path.join(chroot, path, fn))
  except OSError:
    continue
%>\
  % if not stat.S_ISDIR(sres.st_mode):
${format_prefix(fn, sres)} ${file_link(fn)} ${download_link(fn)}
  % else:
${format_prefix(fn, sres)} ${directory_link(fn)}
  % endif
% endfor
    </pre>
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
% else:
<body>
  This task is running without a chroot.
</body>
% endif

</html>
