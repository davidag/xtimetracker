# copy this into ~/.config/fish/completions/ to enable autocomplete for the tt time tracker
#
function __fish_tt_needs_sub -d "provides a list of sub commands"
  set cmd (commandline -opc)
  if [ (count $cmd) -eq 1 -a $cmd[1] = 'tt' ]
    return 0
  end
  return 1
end

function __fish_tt_using_command -d "determine if tt is using the passed command"
  set cmd (commandline -opc)
  if [ (count $cmd) -ge 2 -a $cmd[1] = 'tt' ]
    if [ $argv[1] = $cmd[2] ]
      return 0
    end
    return 1
  end
  return 1
end

function __fish_tt_get_projects -d "return a list of projects"
  command tt projects
end

function __fish_tt_get_tags -d "return a list of tags"
  command tt tags
end

function __fish_tt_has_project -d "determine if tt is using a passed command and if it has a project"
  set cmd (commandline -opc)
  if [ (count $cmd) -gt 2 -a $cmd[1] = 'tt' ]
    if [ $argv[1] = $cmd[2] ]
      if contains "$cmd[3]" (__fish_tt_get_projects)
        return 0
      end
    end
  end
  return 1
end

function __fish_tt_has_from -d "determine if tt is using a passed command and if it is using from"
  set cmd (commandline -opc)
  if [ (count $cmd) -gt 2 -a $cmd[1] = 'tt' ]
    if [ $argv[1] = $cmd[2] ]
      if contains -- "$cmd[3]" -f --from
        return 0
      end
    end
  end
  return 1
end

function __fish_tt_get_frames -d "return a list of frames" #TODO, use tt logs to get more info
  command tt frames
end

function __fish_tt_needs_project -d "check if we need a project"
  set cmd (commandline -opc)
  if [ (count $cmd) -ge 2 -a $cmd[1] = 'tt' ]
    if [ $argv[1] = $cmd[2] ]
      for i in $cmd
        if contains $i (__fish_tt_get_projects)
          return 1 # return 1 because we alredy have a project
        end
      end
      return 0 # we are using $argv as our command and the command does not contain any projects
    end
  end
  return 1
end

# ungrouped
complete -f -c tt -n '__fish_tt_needs_sub' -a cancel -d "Cancel the last start command"
complete -f -c tt -n '__fish_tt_needs_sub' -a frames -d "Display the list of all frame IDs"
complete -f -c tt -n '__fish_tt_needs_sub' -a help -d "Display help information"
complete -f -c tt -n '__fish_tt_needs_sub' -a projects -d "Display the list of projects"
complete -f -c tt -n '__fish_tt_needs_sub' -a tags -d "Display the list of tags"

# add
complete -f -c tt -n '__fish_tt_needs_sub' -a add -d "Add time for project with tag(s) that was not tracked live"
complete -f -c tt -n '__fish_tt_using_command add' -s f -l from -d "Start date for add"
complete -f -c tt -n '__fish_tt_has_from add' -s t -l to -d "end date for add"
complete -f -c tt -n '__fish_tt_using_command add' -s c -l confirm-new-project -d "Confirm addition of new project"
complete -f -c tt -n '__fish_tt_using_command add' -s b -l confirm-new-tag -d "Confirm addition of new tag"

# aggregate
complete -f -c tt -n '__fish_tt_needs_sub' -a aggregate -d "Display a report of the time spent on each project aggregated by day"
complete -f -c tt -n '__fish_tt_using_command aggregate' -s c -l current -d "include the running frame"
complete -f -c tt -n '__fish_tt_using_command aggregate' -s C -l no-current -d "exclude the running frame (default)"
complete -f -c tt -n '__fish_tt_using_command aggregate' -s f -l from -d "Start date for aggregate"
complete -f -c tt -n '__fish_tt_has_from aggregate' -s t -l to -d "end date for aggregate"
complete -f -c tt -n '__fish_tt_using_command aggregate' -s p -l project -d "restrict to project" -a "(__fish_tt_get_projects)"
complete -f -c tt -n '__fish_tt_using_command aggregate' -s T -l tag -d "restrict to tag" -a "(__fish_tt_get_tags)"
complete -f -c tt -n '__fish_tt_using_command aggregate' -s j -l json -d "output json"
complete -f -c tt -n '__fish_tt_using_command aggregate' -s s -l csv -d "output csv"
complete -f -c tt -n '__fish_tt_using_command aggregate' -s g -l pager -d "view through pager"
complete -f -c tt -n '__fish_tt_using_command aggregate' -s G -l no-pager -d "don't vew through pager"

# config
complete -f -c tt -n '__fish_tt_needs_sub' -a config -d "Get and set configuration options"
complete -f -c tt -n '__fish_tt_using_command config' -s e -l edit -d "Edit the config with an editor"

# edit
complete -f -c tt -n '__fish_tt_needs_sub' -a edit -d "Edit a frame"
complete -f -c tt -n '__fish_tt_using_command edit' -a "(__fish_tt_get_frames)"

# log
complete -f -c tt -n '__fish_tt_needs_sub' -a log -d "Display sessions during the given timespan"
complete -f -c tt -n '__fish_tt_using_command log' -s c -l current -d "include the running frame"
complete -f -c tt -n '__fish_tt_using_command log' -s C -l no-current -d "exclude the running frame (default)"
complete -f -c tt -n '__fish_tt_using_command log' -s f -l from -d "Start date for log"
complete -f -c tt -n '__fish_tt_has_from log' -s t -l to -d "end date for log"
complete -f -c tt -n '__fish_tt_using_command log' -s y -l year -d "show the last year"
complete -f -c tt -n '__fish_tt_using_command log' -s m -l month -d "show the last month"
complete -f -c tt -n '__fish_tt_using_command log' -s l -l luna -d "show the last lunar cycle"
complete -f -c tt -n '__fish_tt_using_command log' -s w -l week -d "show week-to-day"
complete -f -c tt -n '__fish_tt_using_command log' -s d -l day -d "show today"
complete -f -c tt -n '__fish_tt_using_command log' -s a -l all -d "show all"
complete -f -c tt -n '__fish_tt_using_command log' -s p -l project -d "restrict to project" -a "(__fish_tt_get_projects)"
complete -f -c tt -n '__fish_tt_using_command log' -s T -l tag -d "restrict to tag" -a "(__fish_tt_get_tags)"
complete -f -c tt -n '__fish_tt_using_command log' -s j -l json -d "output json"
complete -f -c tt -n '__fish_tt_using_command log' -s s -l csv -d "output csv"
complete -f -c tt -n '__fish_tt_using_command log' -s g -l pager -d "view through pager"
complete -f -c tt -n '__fish_tt_using_command log' -s G -l no-pager -d "don't vew through pager"

# merge
complete -f -c tt -n '__fish_tt_needs_sub' -a merge -d "merge existing frames with conflicting ones"
complete -f -c tt -n '__fish_tt_using_command merge' -s f -l force -d "silently merge"

# remove
complete -f -c tt -n '__fish_tt_needs_sub' -a remove -d "Remove a frame"
complete -f -c tt -n '__fish_tt_using_command remove' -a "(__fish_tt_get_frames)"
complete -f -c tt -n '__fish_tt_using_command remove' -s f -l force -d "silently remove"

# rename
complete -f -c tt -n '__fish_tt_needs_sub' -a rename -d "Rename a project or tag"
complete -f -c tt -n '__fish_tt_using_command rename' -a "(__fish_tt_get_projects) (__fish_tt_get_tags)"

# report
complete -f -c tt -n '__fish_tt_needs_sub' -a report -d "Display a report of time spent"
complete -f -c tt -n '__fish_tt_using_command report' -s c -l current -d "include the running frame"
complete -f -c tt -n '__fish_tt_using_command report' -s C -l no-current -d "exclude the running frame (default)"
complete -f -c tt -n '__fish_tt_using_command report' -s f -l from -d "Start date for report"
complete -f -c tt -n '__fish_tt_has_from report' -s t -l to -d "end date for report"
complete -f -c tt -n '__fish_tt_using_command report' -s y -l year -d "show the last year"
complete -f -c tt -n '__fish_tt_using_command report' -s m -l month -d "show the last month"
complete -f -c tt -n '__fish_tt_using_command report' -s l -l luna -d "show the last lunar cycle"
complete -f -c tt -n '__fish_tt_using_command report' -s w -l week -d "show week-to-day"
complete -f -c tt -n '__fish_tt_using_command report' -s d -l day -d "show today"
complete -f -c tt -n '__fish_tt_using_command report' -s a -l all -d "show all"
complete -f -c tt -n '__fish_tt_using_command report' -s p -l project -d "restrict to project" -a "(__fish_tt_get_projects)"
complete -f -c tt -n '__fish_tt_using_command report' -s T -l tag -d "restrict to tag" -a "(__fish_tt_get_tags)"
complete -f -c tt -n '__fish_tt_using_command report' -s j -l json -d "output json"
complete -f -c tt -n '__fish_tt_using_command report' -s s -l csv -d "output csv"
complete -f -c tt -n '__fish_tt_using_command report' -s g -l pager -d "view through pager"
complete -f -c tt -n '__fish_tt_using_command report' -s G -l no-pager -d "don't vew through pager"

# restart
complete -f -c tt -n '__fish_tt_needs_sub' -a restart -d "Restart monitoring time for a stopped project"
complete -f -c tt -n '__fish_tt_using_command restart' -s s -l stop -d "stop running project"
complete -f -c tt -n '__fish_tt_using_command restart' -s S -l no-stop -d "do not stop running project"
complete -f -c tt -n '__fish_tt_using_command restart' -a "(__fish_tt_get_frames)"

# start
complete -f -c tt -n '__fish_tt_needs_sub' -a start -d "Start monitoring time for a project"
complete -f -c tt -n '__fish_tt_needs_project start' -a "(__fish_tt_get_projects)"
complete -f -c tt -n '__fish_tt_has_project start' -a "+(__fish_tt_get_tags)"

# status
complete -f -c tt -n '__fish_tt_needs_sub' -a status -d "Display when the current project was started and time spent"
complete -f -c tt -n '__fish_tt_using_command status' -s p -l project -d "only show project"
complete -f -c tt -n '__fish_tt_using_command status' -s t -l tags -d "only show tags"
complete -f -c tt -n '__fish_tt_using_command status' -s e -l elapsed -d "only show elapsed time"

# stop
complete -f -c tt -n '__fish_tt_needs_sub' -a stop -d "Stop monitoring time for the current project"
complete -f -c tt -n '__fish_tt_using_command stop' -l at -d "Stop frame at this time (YYYY-MM-DDT)?HH:MM(:SS)?"
