##This file deals with compiling the results of structurally mapped sequencing experiments.
import json,os,pprint
from os import listdir
from os.path import join
from Common.Common import structural_map_location,aggregates_location,fetch_antigen_map



#From a single map file, create an aggreagate of sequence identitities.
def process_single_map(loc):
	
	#cdr, frame and full results count the number of percentages (e.g. how many times we got sequence identity of 83%)
	#fread holds the cdrs:
	#h1->
	#--->sequence
	#---->#total,pdb_found,#modelable (as in certain cases because of anchors we might not have been able to model?)	
	results = {'cdr':{},'frame':{},'full':{},'fread':{}}

	data = json.load(open(loc))

	for sequence in data:
		
		for region in data[sequence]:
			if region=='fread':
						
				if data[sequence][region]!=None:
					for cdr in data[sequence][region]:
						fread_data = data[sequence][region][cdr]
						
						#The actual sequence as submitted in the NGS dataset.
						cdr_sequence = fread_data['qu']
						
						if cdr not in results['fread']:
							results['fread'][cdr] = {}
						if cdr_sequence not in results['fread'][cdr]:
							results['fread'][cdr][cdr_sequence] = {'total':0,'pdb':False,'model':0}
						
						results['fread'][cdr][cdr_sequence]['total']+=1
						if fread_data['str'] !=None:
							results['fread'][cdr][cdr_sequence]['model']+=1
							#If the structure we found is identical to the query, say we have a pdb hit.
							if fread_data['qu'] == fread_data['seq']:
								results['fread'][cdr][cdr_sequence]['pdb'] = True
						
						if 'score' not in results['fread'][cdr][cdr_sequence]:
							results['fread'][cdr][cdr_sequence]['score'] = 0

						#The ESS score.
						try:
							score = int(fread_data['scr'])
						except TypeError:#Means there is no score as we did not find a suitable match.
							continue
						#Deal with ESS score. Keep the highest ESS score for the given CDR sequence.
						if results['fread'][cdr][cdr_sequence]['score'] < score:
							results['fread'][cdr][cdr_sequence]['score'] = score
						
				
			else:
				sid = data[sequence][region]['best_sid']
				if sid not in results[region]:
					results[region][sid] = 0
				results[region][sid]+=1
	return results

#Given a dict from regions to sid list, fold the results of the new such list into the current one
def merge_aggregates(current,new):

	for region in new:
		if region == 'fread':
			for cdr in new[region]:
				if cdr not in current[region]:
					current[region][cdr] = {}
				for sequence in new[region][cdr]:
					if sequence not in current[region][cdr]:
						current[region][cdr][sequence] = {'total':0,'pdb':False,'model':0}
					current[region][cdr][sequence]['total']+=new[region][cdr][sequence]['total']
					current[region][cdr][sequence]['model']+=new[region][cdr][sequence]['model']
					
					if new[region][cdr][sequence]['pdb'] == True:
						current[region][cdr][sequence]['pdb'] = True
					if 'score' not in current[region][cdr][sequence]:
						current[region][cdr][sequence]['score'] = 0
					if new[region][cdr][sequence]['score'] > current[region][cdr][sequence]['score']:
						current[region][cdr][sequence]['score'] = new[region][cdr][sequence]['score']
		else:

			for sid in new[region]:
				if sid not in current[region]:
					current[region][sid] = 0
				current[region][sid]+=new[region][sid]
	return current

#Process the results of a single experiment
def process_experiment(exp_name):
	results_location = join(structural_map_location,exp_name)
	i = 0
	aggregate = {'cdr':{},'frame':{},'full':{},'fread':{}}

	for f in sorted(listdir(results_location)):
		i+=1
		print 'Done',i,'files...'
		
		results = process_single_map(join(results_location,f))
		
		#Fold results into the global aggregate.
		aggregate = merge_aggregates(aggregate,results)
	
	#Save aggregate.
	aggregate_target = join(aggregates_location,exp_name)
	if not os.path.exists(aggregate_target):
		os.mkdir(aggregate_target)
	f = open(join(aggregate_target,'aggregate.json'),'w')
	f.write(json.dumps(aggregate))
	f.close()


#From a single map file, create an aggreagate of sequence identitities.
def extract_data(loc,results):
	
	#cdr, frame and full results count the number of percentages (e.g. how many times we got sequence identity of 83%)
	#fread holds the cdrs:
	#h1->
	#--->sequence
	#---->#total,pdb_found,#modelable (as in certain cases because of anchors we might not have been able to model?)	
	

	data = json.load(open(loc))

	for sequence in data:
		
		for region in data[sequence]:
			if region=='fread':
				
				if data[sequence][region]!=None:
					for cdr in data[sequence][region]:
						fread_data = data[sequence][region][cdr]
						
						query = fread_data['qu']
						structure = fread_data['str'][0:4]
						if cdr not in results['cdrs']:
							results['cdrs'][cdr] = {}
						try: 
							results['cdrs'][cdr][structure]['#']+=1
							try:
								results['cdrs'][cdr][structure]['loops'][query]+=1
							except:
								results['cdrs'][cdr][structure]['loops'][query] = 1
						except KeyError:
							results['cdrs'][cdr][structure] = {'#':1,'loops':{query:1}}
							
							#We do not have this pdb, need to create an entry.
						
			else:
				if region == 'cdr':
					continue
				pdb = data[sequence][region]['best_pdb']
				if pdb == 0:#Annotation failure.
					continue
				pdb = pdb[0:4]
				try:
					results[region][pdb]+=1
				except KeyError:
					results[region][pdb] = 1
	return results

#Process the results of a single experiment
def create_summary(exp_name):
	results_location = join(structural_map_location,exp_name)
	i = 0
	
	#Fetch the aggregates.
	antigens = fetch_antigen_map()

	results = {'frame':{},'full':{},'cdrs':{}}

	for f in sorted(listdir(results_location)):
		i+=1
		#print 'Done',i,'files...'
		
		results = extract_data(join(results_location,f),results)
		if i> 100:
			break
		

	stats = {'global':{},'frame':{},'full':{}}

	for region in ['frame','full']:
		
		for pdb in results[region]:
			antigen = ''
			if pdb in antigens:
				antigen = antigens[pdb]
			stats[region][pdb] = {'#':results[region][pdb],'ag':antigen}
			try:
				stats['global'][pdb]['#']+=1
			except KeyError:
				stats['global'][pdb] = {'#':1,'ag':antigen} 
	
	#Get the most common PDBs for cdrs.
	for cdr in results['cdrs']:
		
		stats[cdr] = []
		for pdb in results['cdrs'][cdr]:
			antigen = ''
			if pdb in antigens:
				antigen = antigens[pdb]
			stats[cdr].append({'#':results['cdrs'][cdr][pdb]['#'],'pdb':pdb,'ag':antigen})
			try:
				stats['global'][pdb]['#']+=1
			except KeyError:
				stats['global'][pdb] = {'#':1,'ag':antigen} 
			#print pdb,results['cdrs'][cdr][pdb]['#']
		#Top 50
		#stats[cdr] = sorted(stats[cdr],reverse=True)[0:min(len(stats[cdr]),10)]
		#print cdr, stats[cdr]
		#Fold results into the global aggregate.
		#aggregate = merge_aggregates(aggregate,results)
	import pprint
	pprint.pprint(stats)
	
	#TODO top10.


	

if __name__ == '__main__':
	
	import sys
	
	cmd = sys.argv[1]

	#Creating aggregates for plotting
	if cmd == 'create_aggregate':#Usage: python StructuralResults.py create_aggregate [experiment name]
		#Create aggregate given experiment name
		process_experiment(sys.argv[2])
	
	#Create summary results.
	if cmd == 'summary':
		create_summary(sys.argv[2])

	###########
	#DEBUGGING#
	###########

	if cmd == 'debug_single':#Debugging processing single maps
		exp_name = 'sample'
		results_location = join(structural_map_location,exp_name)
		for f in sorted(listdir(results_location)):
			print process_single_map(join(results_location,f))
	if cmd == 'debug_multiple':#Debugging processing multiple maps
		exp_name = 'sample'
		results_location = join(structural_map_location,exp_name)
		i = 0
		aggregate = {'cdr':{},'frame':{},'full':{},'fread':{}}

		for f in sorted(listdir(results_location)):
			i+=1
			print i
		
			results = process_single_map(join(results_location,f))
		
			#Fold results into the global aggregate.
			aggregate = merge_aggregates(aggregate,results)
	
		#Save aggregate.
		aggregate_target = join(aggregates_location,exp_name)
		if not os.path.exists(aggregate_target):
			os.mkdir(aggregate_target)
		f = open(join(aggregate_target,'aggregate.json'),'w')
		f.write(json.dumps(aggregate))
		f.close()
	

	pass
