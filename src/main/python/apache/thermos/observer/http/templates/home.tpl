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

 <html>
<title>thermos(${hostname})</title>

<link rel="stylesheet"
      type="text/css"
      href="/assets/bootstrap.css"/>
<link rel="stylesheet" type="text/css" href="/assets/navbar.css"/>
<body>
<nav class="navbar">
  <div class="container">
    <div class="navbar-header">
      <a class="navbar-brand" href="${scheduler_web_url}/scheduler"><img alt="Brand" src="/assets/aurora_logo_white.png"></a>
    </div>
    <ul class="nav navbar-nav navbar-right">
      <li><a href="${scheduler_web_url}/updates">updates</a></li>
    </ul>
  </div>
</nav>

<%!
 import socket
 import time

 def pretty_time(seconds):
   return time.asctime(time.localtime(seconds))
%>

<div class="container">
  <h3> host ${socket.gethostname()} </h3>

  <div class="content" id="defaultLayout">
     <table class="zebra-striped">
     <thead>
       <tr>
         <th colspan=3> task </th>
         <th colspan=4> resources </th>
         <th colspan=3> links </th>
       </tr>

       <tr>
         <th> name </th> <th> role </th> <th> status </th>
         <th> procs </th> <th> cpu </th> <th> ram </th> <th> disk </th>
         <th> task </th> <th> chroot </th> <th> ports </th>
       </tr>
      </thead>
      <tbody>

      % for proc_name, proc in sorted(processes.items()):
       <tr>
         <td> ${proc["process_name"]} </td>
         <td> ${proc["process_run"]} </td>
         <td> ${proc["state"]} </td>
         <td> ${pretty_time(float(proc["start_time"])/1000.0) if "start_time" in proc else ""} </td>
         <td> ${pretty_time(float(proc["stop_time"])/1000.0) if "stop_time" in proc else ""} </td>
         <td> ${'%.3f' % proc["used"]["cpu"] if "used" in proc else ""} </td>
         <td> ${'%dMB' % (proc["used"]["ram"] / 1024 / 1024) if "used" in proc else ""} </td>
         <td> <a href="/logs/${task_id}/${proc["process_name"]}/${proc["process_run"]}/stdout">stdout</a> </td>
         <td> <a href="/logs/${task_id}/${proc["process_name"]}/${proc["process_run"]}/stderr">stderr</a> </td>
       </tr>
      % endfor
     </tbody>
     </table>
  </div>

</div>

</body>
</html>
