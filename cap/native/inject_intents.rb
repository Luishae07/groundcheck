#!/usr/bin/env ruby
# Adds GroundcheckIntents.swift to the Capacitor-generated Xcode project's
# App target — `cap add ios` only knows about Capacitor's own files, so a
# hand-written native file has to be registered into the .xcodeproj
# programmatically after the fact. Run from the repo root; expects the
# Swift file to already be copied into cap/ios/App/App/.
require 'xcodeproj'

project_path = 'cap/ios/App/App.xcodeproj'
project = Xcodeproj::Project.open(project_path)
target = project.targets.find { |t| t.name == 'App' }
raise "App target not found" unless target

group = project.main_group.find_subpath('App', true)
file_ref = group.new_reference('GroundcheckIntents.swift')
target.add_file_references([file_ref])

project.save
puts "Added GroundcheckIntents.swift to #{project_path}"
