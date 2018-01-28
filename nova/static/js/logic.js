var http = require('http');
var fs = require('fs');

var file = fs.createWriteStream("file.txt");
var request = http.get("http://runbot.vauxoo.com/runbot/static/build/14375-1662-128527/logs/job_20_test_all.txt", function(response) {
  response.pipe(file);
});
$( "li.active" ).bind( "click", function() {
    var filePath = 'file.txt';
    var file = fs.readFileSync(filePath);
    console.log('Initial File content : ' + file);

    fs.watchFile(filePath, function() {
        console.log('File Changed ...');
        file = fs.readFileSync(filePath);
        console.log('File content at : ' + new Date() + ' is \n' + file);
        var file = fs.createWriteStream("file.txt");
        var request = http.get("http://runbot.vauxoo.com/runbot/static/build/14375-1662-128527/logs/job_20_test_all.txt", function(response) {
          response.pipe(file);
        });
    });
});
