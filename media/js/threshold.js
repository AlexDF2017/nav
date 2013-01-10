/* -*- coding: utf-8 -*-
 *
 * Threshold specific javascripts
 *
 * Copyright (C) 2011 UNINETT AS
 *
 * This file is part of Network Administration Visualized (NAV).
 *
 * NAV is free software: you can redistribute it and/or modify it under
 * the terms of the GNU General Public License version 2 as published by
 * the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful, but WITHOUT
 * ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
 * FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
 * more details.  You should have received a copy of the GNU General Public
 * License along with NAV. If not, see <http://www.gnu.org/licenses/>.
 *
 */

if(!Array.indexOf){
    Array.prototype.indexOf = function(obj){
        for(var i=0; i<this.length; i++){
            if(this[i]==obj){
                return i;
            }
        }
        return -1;
    }
}

/*
 * A simple timer-function that will call the given "callback"
 * after a timeout(given in millisecs).
*/
var typeDelay = function(){
    var timer = 0;
    return function(callback, ms){
        clearTimeout (timer);
        timer = setTimeout(callback, ms);
    }  
}();

/*
 * Declare a separate namespace for all variables and functions related to
 * the threshold-webpages.
*/
var threshold = threshold || {};

/* Used as a semaphore to block out concurrent ajax-calls to netbox-search. */
threshold.netboxSearchReq = null;
/* Used as a semaphore to block out concurrent ajax-calls to bulkset */
threshold.getBulkUpdateHtmlReq = null;
/* Used as a semaphore to block out concurrent ajax-calls to chooseDevice */
threshold.chooseDeviceTypeReq = null;
/* netbox- or interface-mode */
threshold.displayMode = '';
threshold.stdBgColor = 'white';
threshold.stdErrColor = 'red';
threshold.stdSuccessColor = 'green';
threshold.perCentRepl = new RegExp('%*$');
threshold.descriptionRegExp = new RegExp('^[a-zA-Z][a-zA-Z0-9\ ]+$');
threshold.thresholdSaveStatus = 0;
threshold.saveMessage = null;

/*
 * Kind of a semaphore to block out concurrent ajax-calls for
 * save_threshold.
*/
threshold.save_queue =  new Array();

threshold.removeFromQueue = function(id){
    var idx = threshold.save_queue.indexOf(id);
    if(idx > -1){
	threshold.save_queue.splice(idx, 1);
    }
};

threshold.backToSearch = function(){
    $('div.#netboxsearch').show();
    if(threshold.displayMode == 'interface'){
        $('div.#interfacesearch').show();
    }
    var bulkUpdateData = $('div.#bulkupdateDiv');
    $(bulkUpdateData).hide();
    $(bulkUpdateData).empty();
    threshold.removeMessages();
};

threshold.removeMessages = function(){
    var messagesDiv = $('div.#messagesDiv');
    $(messagesDiv).empty();
};

threshold.updateMessages = function(msg, isError){
    var messagesDiv = $('div.#messagesDiv');
    $(messagesDiv).append('<ul><li>' + msg + '</li></ul>');
    if(isError){
        $(messagesDiv).css('color', threshold.stdErrColor);
    } else {
        $(messagesDiv).css('color', threshold.stdSuccessColor);
    }
};

threshold.pageNotFound = function(){
    threshold.updateMessages('Page not found', true);
    return -1;
};

threshold.serverError = function(){
    threshold.updateMessages('Internal server-error', true);
    return -1;
};

threshold.ajaxError = function( request, errMessage, errType){
    var errMsg = 'Error: ' + errMessage + '; ' + errType;
    threshold.updateMessages(errMsg, true);
    return -1;
};

threshold.isLegalDescription = function(desc){
    return desc.match(threshold.descriptionRegExp);
};

threshold.showAjaxLoader = function(){
    $('span.ajaxLoader').show();
};

threshold.hideAjaxLoader = function(){
    $('span.ajaxLoader').hide();
};

/*
 * Takes a table and makes it a string.  Each element from the table
 * is separated with the character "|" in the string.
*/
threshold.table2String = function(tab){
    var len = tab.length;
    var ret_str = '';
    for(var i = 0; i < len; i++){
        if(i > 0 ){
            ret_str += '|';
        }
        ret_str += tab[i];
    }
    return ret_str;   
};

threshold.toggleIncludes = function(){
    var checkBox = $('input:checkbox[name="toggleIncludes"]');
    if($(checkBox).attr('checked')){
        threshold.checkAllInclude();
    } else {
        threshold.unCheckAllInclude();
    }
};

threshold.checkAllInclude = function(){
    var allIncludes = $('input:checkbox[name="include"]') || [];
    for(var i = 0; i < allIncludes.length; i++){
        allIncludes[i].checked = true;
    }
};

threshold.unCheckAllInclude = function(){
    var allIncludes = $('input:checkbox[name="include"]:checked') || [];
    for(var i = 0; i < allIncludes.length; i++){
        allIncludes[i].checked=false;
    }
};

threshold.stripPerCentSymbol = function(str){
    return str.replace(threshold.perCentRepl, '');
};

/*
 * NB!
 * Always remember to keep error-chekcing here and on server in sync!
*/
threshold.isLegalThreshold = function(thr){
    if( thr.length == 0){
        return true;
    }
    var intValue = parseInt(threshold.stripPerCentSymbol(thr));
    return (! isNaN(intValue));
    
};

threshold.setChangedThreshold = function(inp){
    $(inp).parent().removeClass();
    $(inp).parent().addClass('changed');
};

threshold.showSavedThreshold = function(inp){
    var par = $(inp).parent();
    $(par).removeClass('changed');
    $(par).css('background-color', threshold.stdSuccessColor);
    $(par).fadeTo(2000, 0.6);
    $(par).fadeTo(2000, 1.0, function(){
        $(par).css('background-color', threshold.stdBgColor);
        $(par).show();
    });
    return true;
};

threshold.showErrorThreshold = function(inp){
    $(inp).parent().removeClass();
    $(inp).parent().addClass('error');
};

threshold.netboxSearch = function(){
    if(threshold.netboxSearchReq) {
        /* The previous ajax-call is cancelled and replaced with the last */
        threshold.netboxSearchReq.abort();
    }
    threshold.showAjaxLoader();
    threshold.removeMessages();
    var retVal = 0;

    var descr = $('select.#descr').val();
    var sysname = $('input.#netboxname').val();
    // The checkboxes for GW, GSW and SW
    var checkBoxList = $('input:checkbox[name="boxtype"]:checked');
    var vendor = $('select.#vendor').val();
    var model = $('select.#model').val();
    var ifname = $('input.#interfacename').val();
    var upDown = $('input:checkbox[name="updown"]:checked').val();

    var boxes = $('select.#chosenboxes').val() || [];
    
    if(descr == 'empty'){
        return -1;
    }
    if(! threshold.isLegalDescription(descr)){
        threshold.updateMessages('Illegal threshold description', true);
        return -1;
    }
    var inputData = { 'descr': descr };

    if(sysname.length > 0){
        inputData['sysname'] = sysname;
    }

    if(vendor != 'empty'){
        inputData['vendor'] = vendor;
    }
    if(model != 'empty'){
        inputData['model'] = model;
    }

    if(ifname.length > 0){
        inputData['ifname'] = ifname;
    }

    if(upDown == 'updown'){
        inputData['updown'] = upDown;
    }
    
    var chosenboxes = ''
    if(boxes.length > 0 ){
        inputData['boxes'] = threshold.table2String(boxes);
    }
    
    var len = checkBoxList.length;
    for(var i = 0; i < len; i++){
        inputData[checkBoxList[i].value] = checkBoxList[i].value;
    }
    threshold.netboxSearchReq = $.ajax({ url: '/threshold/netboxsearch/',
             data: inputData,
             dataType: 'json',
             type: 'POST',
             success: function(data, textStatus, header){
                            if(data.error){
                                threshold.updateMessages(data.message, true);
                                retVal = -1;
                                return retVal;
                            }
                            $('select.#chosenboxes').empty();
                            $('select.#chosenboxes').append(data.foundboxes);
                            $('select.#choseninterfaces').empty();
                            $('select.#choseninterfaces').append(data.foundinterfaces);
                            if(data.types){
                                $('select.#model').empty();
                                $('select.#model').append(data.types);
                            }
                            return retVal;
                     },
             error: function(req, errMsg, errType){
                        return threshold.ajaxError(req, errMsg, errType);
                    },
             complete: function(header, textStatus){
                        threshold.netboxSearchReq = null;
                        return 0;
                       },
             statusCode: {404: function(){
                                return threshold.pageNotFound();
                               },
                          500: function(){
                                return threshold.serverError();
                               }
                        }
        });
    threshold.hideAjaxLoader();
    return retVal;
};


threshold.getBulkUpdateHtml = function(descr, ids){
    if(threshold.getBulkUpdateHtmlReq){
        /* The previous ajax-call is cancelled and replaced with the last */
        threshold.getBulkUpdateHtmlReq.abort();
    }
    if(! threshold.isLegalDescription(descr)){
        threshold.updateMessages('Illegal threshold description', true);
        return -1;
    }
    var inputData = {
        'descr': descr,
        'ids': ids
        };
    threshold.getBulkUpdateHtmlReq =
        $.ajax({url: '/threshold/preparebulk/',
                data: inputData,
                dataType: 'text',
                type: 'POST',
                success: function(data, textStatus, header){
                            if(data.error){
                                threshold.updateMessages(data.message, true);
                                return -1;
                            }
                            $('div.#netboxsearch').hide();
                            $('div.#interfacesearch').hide();
                            $('div.#bulkupdateDiv').show();
                            $('div.#bulkupdateDiv').html(data);
                            return 0;
                        },
                error: function(req, errMsg, errType){
                        return threshold.ajaxError(req, errMsg, errType);
                       },
                complete: function(header, textStatus){
                            threshold.getBulkUpdateHtmlReq = null;
                            return 0;
                          },
                statusCode: {404: function(){
                                    return threshold.pageNotFound();
                                },
                             500: function(){
                                    return threshold.serverError();
                                }
                        }
            });

};

threshold.chooseDeviceType = function(the_select, select_val){
    if(threshold.chooseDeviceTypeReq){
        /* The previous ajax-call is cancelled and replaced with the last */
        threshold.chooseDeviceTypeReq.abort();
    }
    threshold.chooseDeviceTypeReq =
        $.ajax({url: '/threshold/choosetype/',
            data: {'descr': select_val},
            dataType: 'json',
            type: 'POST',
            success: function(data, textStatus, header){
                        if(data.error){
                            threshold.updateMessages(data.Message, true);
                            return -1;
                        } 
                        threshold.displayMode = data.message;
                        threshold.netboxSearch();
                        if(threshold.displayMode == 'interface'){
                            $(document).find('div.#netboxSubmitDiv').hide();
                            $(document).find('div.#netboxsearch').show();
                            $(document).find('div.#interfacesearch').show();
                            $(document).find('div.#interfaceSubmitDiv').show();
                        }
                        if(threshold.displayMode == 'netbox'){
                            $(document).find('div.#interfaceSubmitDiv').hide();
                            $(document).find('div.#interfacesearch').hide();
                            $(document).find('div.#netboxsearch').show();
                            $(document).find('div.#netboxSubmitDiv').show();
                        }
                        return 0;
                      },
            error: function(req, errMsg, errType){
                        return threshold.ajaxError(req, errMsg, errType);
                    },
            complete: function(header, textStatus){
                        threshold.chooseDeviceTypeReq = null;
                        return 0;
                      },
            statusCode: {404: function(){
                                return threshold.pageNotFound();
                               },
                         500: function(){
                                return threshold.serverError();
                              }
                        }
          });
};

threshold.saveToServer = function(toSave){
    threshold.saveMessage = null;
    threshold.thresholdSaveStatus = 0;
    var objectJSON = $.toJSON(toSave);

    $.ajax({url: '/threshold/thresholdssave/',
            data: {'thresholds': objectJSON},
            dataType: 'json',
            type: 'POST',
            async: false,
            success: function(data, textStatus, header){
                        if(typeof data.error == 'undefined' ){
                            threshold.thresholdSaveStatus = -1;
                            return -1;
                        }
                        if(data.error > 0){
                            threshold.thresholdSaveStatus = -1;
                            threshold.saveMessage = data;
                            return -1;
                        }
                        return 0;
                     },
            error:  function(req, errMsg, errType){
                        threshold.thresholdSaveStatus = -1;
                        return threshold.ajaxError(req, errMsg, errType);
                    },
            complete: function(header, textStatus){
                        return 0;
                      },
            statusCode: {404: function(){
                                threshold.thresholdSaveStatus = -1;
                                return threshold.pageNotFound();
                              },
                         500: function(){
                                threshold.thresholdSaveStatus = -1;
                                return threshold.serverError();
                              }
                        }

            });
    return threshold.thresholdSaveStatus;
};

threshold.findCheckBox = function(name, value){
    var findStr = 'input:checkbox[name="'+ name + '"]';
    if(value != null){
        findStr += '[value="' + value +'"]';
    }
    return $(findStr);
};

threshold.saveChosenThresholds = function(allIncludes){
    threshold.removeMessages();
    threshold.showAjaxLoader();
    /* Holds an dict of id, operator and threshold-value */
    var thresholdsToSave = new Array();
    /* An array with ids to update the GUI */
    var chosenIds = new Array();
    for(var i = 0; i < allIncludes.length; i++){
        var chkbox = allIncludes[i];
        var dsId = $(chkbox).val();
        var row = $(chkbox).parents('tr');
        var op = $(row).find('select').val();
        var thrInput = $(row).find('input.#threshold');
        var thrVal = $(thrInput).val();
        thresholdsToSave[i] = {'dsId' : dsId, 'op': op, 'thrVal': thrVal};
        chosenIds[i] = dsId;
    }
    var saveStatus = 0;
    if(thresholdsToSave.length > 0){
        saveStatus = threshold.saveToServer(thresholdsToSave);
    }
    if(saveStatus == -1){
        var serverMsg = null;
        if(threshold.saveMessage != null){
            /*
             * Something went wrong,- preserve the error-messages from
             * the server
            */
            serverMsg = threshold.saveMessage;
        } else {
            /*
             * Something went wrong,- but we do not know what...
             * Usually a crash on the server.
             * All thresholds are signaled as withdrawn.
            */
            serverMsg = {};
            serverMsg.message = 'Save failed'
            serverMsg.failed = chosenIds.slice();
            serverMsg.error = serverMsg.failed.length;
        }
        threshold.updateMessages(serverMsg.message, true);
        for(var i = 0; i < serverMsg.failed.length; i++){
            var dsId = serverMsg.failed[i];
            var chkbox = threshold.findCheckBox('include', dsId);
            var thrInput = $(chkbox).parents('tr').find('input.#threshold');
            threshold.showErrorThreshold(thrInput);
            /* Remove those who dis not get saved */
            var idx = chosenIds.indexOf(dsId);
            if(idx > -1){
                chosenIds.splice(idx, 1);
            }
        }
    }
    for(var i = 0; i < chosenIds.length; i++){
        var chkbox = threshold.findCheckBox('include', chosenIds[i]);
        var thrInput = $(chkbox).parents('tr').find('input.#threshold');
        threshold.showSavedThreshold(thrInput);
    }
    threshold.hideAjaxLoader();
    return 0;
};

threshold.saveSingleThreshold = function(btn){
    threshold.removeMessages();
    var row = $(btn).parents('tr');
    var thrInput = $(row).find('input.#threshold');
    var thrVal = $(thrInput).val();
    if(! threshold.isLegalThreshold(thrVal)){
        threshold.updateMessages('Save failed. Illegal threshold', true);
        threshold.showErrorThreshold(thrInput);
        return -1;
    }       

    var chkbox= $(row).find('input:checkbox[name="include"]');
    threshold.saveChosenThresholds([chkbox]);
    return 0;
};

threshold.saveCheckedThresholds = function(){
    //threshold.removeMessages();
    var allIncludes = $('input:checkbox[name="include"]:checked') || [];
    if(allIncludes.length < 1){
        threshold.updateMessages('Please, check the ones to save', true);
        return -1;
    }
    threshold.saveChosenThresholds(allIncludes);
    return 0;
};

threshold.saveAllThresholds = function(){
    threshold.removeMessages();
    var allIncludes = $('input:checkbox[name="include"]') || [];
    if(allIncludes.length < 1){
        return -1;
    }
    threshold.saveChosenThresholds(allIncludes);
    return 0;
};

threshold.bulkUpdateThresholds = function(btn){
    threshold.removeMessages();
    var allIncludes = $('input:checkbox[name="include"]:checked') || [];

    var bulkRow = $(btn).parents('tr');
    var bulkOperator = $(bulkRow).find('select').val();
    var bulkThrInput= $(bulkRow).find('input.#bulkThreshold');
    var bulkThr = $(bulkThrInput).val();

    if(! threshold.isLegalThreshold(bulkThr)){
        threshold.updateMessages('Illegal threshold', true);
        threshold.showErrorThreshold(bulkThrInput);
        return -1;
    }

    if(allIncludes.length < 1){
        threshold.updateMessages('Please, check the ones to update', true);
        return -1;
    }

    $(bulkThrInput).parent().removeClass();
    for(var i = 0; i < allIncludes.length; i++){
        var dsId = allIncludes[i].value;
        var chkbox = $('input:checkbox[value="'+dsId+'"]:checked');
        var row = $(chkbox).parents('tr');

        $(row).find('select').val(bulkOperator);

        var thrInput = $(row).find('input.#threshold');
        $(thrInput).val(bulkThr);
        // Mark as changed
        threshold.setChangedThreshold(thrInput);
        
    }
};

$(document).ready(function(){
    NAV.addGlobalAjaxHandlers();
    $('select.#descr').change(function(){
        var sval = $(this).val();
        if(sval == 'empty'){
            return -1;
        }
        threshold.removeMessages();
        if(! threshold.isLegalDescription(sval)){
            threshold.updateMessages('Illegal threshold description', true);
            return -1;
        }
        $('div.#bulkupdateDiv').hide();
        threshold.chooseDeviceType(this, sval);
    });

    $('input.#netboxname').keyup(function(){
        typeDelay(function(){
            threshold.netboxSearch();
        }, 300);
    });

    $('input:checkbox').change(function(){
        threshold.netboxSearch();
    });

    $('select.#vendor').change(function(){
        threshold.netboxSearch();
    });
        
    $('select.#model').change(function(){
        threshold.netboxSearch();
    });

    $('select.#chosenboxes').change(function(){
        if(threshold.displayMode == 'interface'){
            threshold.netboxSearch();
        }
    });
    
    $('input.#interfacename').keyup(function(){
        typeDelay(function(){
            threshold.netboxSearch();
        }, 300);
    });

    $('input.#netboxsubmit').click(function(){
        threshold.showAjaxLoader();
        threshold.removeMessages();
        var retVal = 0;
        var descr = $('select.#descr').val();
        var boxes = $('select.#chosenboxes').val() || [];
        if(boxes.length > 0){
            threshold.getBulkUpdateHtml(descr, threshold.table2String(boxes));
        } else {
            threshold.updateMessages('No netboxes chosen', true);
            retVal = -1;
        }
        threshold.hideAjaxLoader();
        return retVal;
    });

    $('input.#interfacesubmit').click(function(){
        threshold.showAjaxLoader();
        threshold.removeMessages();
        var retVal = 0;
        var descr = $('select.#descr').val();
        var interfaces = $('select.#choseninterfaces').val() || [];
        if(interfaces.length > 0){
            threshold.getBulkUpdateHtml(descr, threshold.table2String(interfaces));
        } else {
            threshold.updateMessages('No interfaces chosen', true);
            retVal = -1;
        }
        threshold.hideAjaxLoader();
        return retVal;
    });

    $('img.toggler').click(function(){
        $(this).parent().find('img.#plus').toggle();
        $(this).parent().find('img.#minus').toggle();
	$(this).parent().parent().find('table.vertitable').toggle();
    });

    $('div.netboxcontainer').find('input.button').each(function(){
        $(this).click(function(){
	    var dsid = $(this).parent().attr('data_dsid');
	    var thrVal = $(this).parents('tr').find('input.thresholdvalue').val();
            var operator = $(this).parents('tr').find('select').val();
            threshold.save_threshold(this, dsid, operator, thrVal);
        });
		
    });

    $('input.thresholdvalue').change(function(){
        threshold.setChangedThreshold(this);
    });
});


threshold.save_threshold = function(updateButton, dsId, op, thrVal){
    threshold.removeMessages();
    if( threshold.save_queue.indexOf(dsId) > -1){
	return -1;
    }
    threshold.save_queue.push(dsId);
    var thrRecord = {'dsId': dsId, 'op': op, 'thrVal': thrVal};
    var retVal = threshold.saveToServer([thrRecord]);
    if(retVal == -1){
        threshold.callbackFail(updateButton);
        if(threshold.saveMessage != null){
            threshold.updateMessages(threshold.saveMessage.message, true);
        } else {
            threshold.updateMessages('Save failed', true);
        }
    } else {
        threshold.callbackSuccess(updateButton);
    }
    threshold.removeFromQueue(dsId);
    return 0;
};

threshold.callbackSuccess = function(button){
    var maxColumn = $(button).parents("tr").find("td.maxvalue");
    var thrInput = $(button).parents('tr').find('input.thresholdvalue');

    threshold.showSavedThreshold(thrInput);
};

threshold.callbackFail = function(button){
    var thrInput = $(button).parents('tr').find('input.thresholdvalue');
    threshold.showErrorThreshold(thrInput);
};
