# ###################################################
# Copyright (C) 2008-2017 The Unknown Horizons Team
# team@unknown-horizons.org
# This file is part of Unknown Horizons.
#
# Unknown Horizons is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the
# Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
# ###################################################

from itertools import product

from horizons.command.building import Build, Tear
from horizons.command.unit import CreateUnit
from horizons.component.storagecomponent import StorageComponent
from horizons.constants import BUILDINGS, RES, UNITS
from horizons.util.worldobject import WorldObject, WorldObjectNotFound
from horizons.world.production.producer import Producer
from tests.game import game_test, settle


@game_test()
def test_lumberjack(s, p):
	"""
	Lumberjack will produce boards out of wood, collected from nearby trees.
	"""
	settlement, island = settle(s)

	jack = Build(BUILDINGS.LUMBERJACK, 30, 30, island, settlement=settlement)(p)
	assert jack

	assert jack.get_component(StorageComponent).inventory[RES.BOARDS] == 0
	assert jack.get_component(StorageComponent).inventory[RES.TREES] == 0

	for (x_off, y_off) in product([-2, 2], repeat=2):
		x = 30 + x_off
		y = 30 + y_off
		tree = Build(BUILDINGS.TREE, x, y, island, settlement=settlement)(p)
		assert tree
		tree.get_component(Producer).finish_production_now()

	s.run(seconds=30)

	assert jack.get_component(StorageComponent).inventory[RES.BOARDS]


@game_test()
def test_hunter(s, p):
	"""
	Hunter will produce food from dear meat. No animals were harmed in this test.
	"""
	settlement, island = settle(s)

	hunter = Build(BUILDINGS.HUNTER, 30, 30, island, settlement=settlement)(p)
	assert hunter

	assert hunter.get_component(StorageComponent).inventory[RES.FOOD] == 0
	assert hunter.get_component(StorageComponent).inventory[RES.DEER_MEAT] == 0

	for (x_off, y_off) in product([-5, -4, 4, 5], repeat=2):
		x = 30 + x_off
		y = 30 + y_off
		animal = CreateUnit(island.worldid, UNITS.WILD_ANIMAL, x, y)(None)
		# wild animals are slow eaters, we feed them directly
		animal.get_component(StorageComponent).inventory.alter(12, 10)
		animal.get_component(Producer).finish_production_now()
		assert animal

	s.run(seconds=30)

	assert hunter.get_component(StorageComponent).inventory[RES.FOOD]


@game_test()
def test_fisherman(s, p):
	"""
	A fisherman produces food out of fish, collecting in nearby fish deposits.
	"""
	settlement, island = settle(s)

	for x in (25, 30, 35):
		school = Build(BUILDINGS.FISH_DEPOSIT, x, 18, s.world, ownerless=True)(None)
		assert school
		school.get_component(Producer).finish_production_now()

	fisherman = Build(BUILDINGS.FISHER, 25, 20, island, settlement=settlement)(p)
	assert fisherman

	assert fisherman.get_component(StorageComponent).inventory[RES.FOOD] == 0
	assert fisherman.get_component(StorageComponent).inventory[RES.FISH] == 0

	s.run(seconds=20)

	assert fisherman.get_component(StorageComponent).inventory[RES.FOOD]


@game_test()
def test_brick_production_chain(s, p):
	"""
	A brickyard makes bricks from clay. Clay is collected by a clay pit on a deposit.
	"""
	settlement, island = settle(s)

	assert Build(BUILDINGS.CLAY_DEPOSIT, 30, 30, island, ownerless=True)(None)
	assert Build(BUILDINGS.CLAY_PIT, 30, 30, island, settlement=settlement)(p)

	brickyard = Build(BUILDINGS.BRICKYARD, 30, 25, island, settlement=settlement)(p)
	assert brickyard.get_component(StorageComponent).inventory[RES.BRICKS] == 0
	assert brickyard.get_component(StorageComponent).inventory[RES.CLAY] == 0

	s.run(seconds=60) # 15s clay pit, 15s brickyard

	assert brickyard.get_component(StorageComponent).inventory[RES.BRICKS]


@game_test()
def test_tool_production_chain(s, p):
	"""
	Check if a iron mine gathers raw iron, a smeltery produces iron ingots, boards are converted
	to charcoal and tools are produced.

	Pretty much for a single test, but these are rather trivial in their assertions anyway.
	"""
	settlement, island = settle(s)

	assert Build(BUILDINGS.MOUNTAIN, 30, 35, island, ownerless=True)(None)
	assert Build(BUILDINGS.MINE, 30, 35, island, settlement=settlement)(p)

	charcoal = Build(BUILDINGS.CHARCOAL_BURNER, 25, 35, island, settlement=settlement)(p)
	assert charcoal
	charcoal.get_component(StorageComponent).inventory.alter(RES.BOARDS, 10) # give him boards directly

	assert Build(BUILDINGS.SMELTERY, 25, 30, island, settlement=settlement)(p)

	toolmaker = Build(BUILDINGS.TOOLMAKER, 22, 32, island, settlement=settlement)(p)
	assert toolmaker
	toolmaker.get_component(StorageComponent).inventory.alter(RES.BOARDS, 10) # give him boards directly

	assert toolmaker.get_component(StorageComponent).inventory[RES.TOOLS] == 0
	s.run(seconds=120)
	assert toolmaker.get_component(StorageComponent).inventory[RES.TOOLS]

@game_test()
def test_build_tear(s, p):
	"""
	Build stuff and tear it later
	"""
	settlement, island = settle(s)
	tree = Build(BUILDINGS.TREE, 30, 35, island, settlement=settlement)(p)

	s.run(seconds=1)

	wid = tree.worldid
	Tear(tree)(p)

	try:
		WorldObject.get_object_by_id(wid)
	except WorldObjectNotFound:
		pass # should be gone
	else:
		assert False


@game_test(timeout=60)
def test_tree_wood_production(s, p):
	"""
	Check whether trees produce wood
	"""
	settlement, island = settle(s)

	tree = Build(BUILDINGS.TREE, 30, 35, island, settlement=settlement)(p)

	inv = tree.get_component(StorageComponent).inventory

	for i in range(20):  # we want to produce 20 tons of wood

		# wait for a ton of wood to get produced
		while inv[RES.TREES] < 1:
			s.run(seconds=5)

		# take one away to free inventory storage space
		inv.alter(RES.TREES, -1)

	# after producing 20 tons of wood inventory should be empty
	assert inv[RES.TREES] == 0


@game_test(timeout=60)
def test_tree_wildanimalfood_production(s, p):
	"""
	Check whether trees produce wild animal food
	"""
	settlement, island = settle(s)

	tree = Build(BUILDINGS.TREE, 30, 35, island, settlement=settlement)(p)

	inv = tree.get_component(StorageComponent).inventory

	for i in range(20):  # we want to produce 20 units of food

		# wait for a unit of food to get produced
		while inv[RES.WILDANIMALFOOD] < 1:
			s.run(seconds=5)

		# take one away to free inventory storage space
		inv.alter(RES.WILDANIMALFOOD, -1)

	# after producing 20 units of food inventory should be empty
	assert inv[RES.WILDANIMALFOOD] == 0


@game_test()
def test_weaver_production_chain(s, p):
	"""
	Lamb wool is generated by sheep at a pasture to be later transferred to a weaver
	for textile production
	"""
	settlement, island = settle(s)
	
	assert Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.PASTURE, 26, 30, island, settlement=settlement)(p)
	
	weaver = Build(BUILDINGS.WEAVER, 30, 26, island, settlement=settlement)(p)
	
	assert weaver
	
	assert weaver.get_component(StorageComponent).inventory[RES.WOOL] == 0
	assert weaver.get_component(StorageComponent).inventory[RES.TEXTILE] == 0
	s.run(seconds=60) # 30s pasture, 30s weaver
	assert weaver.get_component(StorageComponent).inventory[RES.TEXTILE]


@game_test()
def test_pavilion_production(s, p):
	"""
	Check whether the pavilion produces faith
	"""
	settlement, island = settle(s)
	pavilion = Build(BUILDINGS.PAVILION, 30, 30, island, settlement=settlement)(p)

	assert pavilion
	assert pavilion.get_component(StorageComponent).inventory[RES.FAITH] == 0
	s.run(seconds=30)
	assert pavilion.get_component(StorageComponent).inventory[RES.FAITH]


@game_test()
def test_farm_production(s, p):
	"""
	Check whether fields produce resources and the farm transforms them actual goods
	"""
	
	settlement, island = settle(s)
	farm = Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	
	assert farm
	
	primary_resources = (RES.LAMB_WOOL, RES.POTATOES, RES.RAW_SUGAR, RES.TOBACCO_PLANTS, RES.CATTLE, RES.PIGS, RES.HERBS, 
						 RES.GRAIN, RES.SPICE_PLANTS, RES.COCOA_BEANS, RES.VINES, RES.ALVEARIES, RES.HOP_PLANTS)

	secondary_resources = (RES.WOOL, RES.FOOD, RES.SUGAR, RES.TOBACCO_LEAVES, RES.CATTLE_SLAUGHTER, RES.PIGS_SLAUGHTER, 
						   RES.MEDICAL_HERBS, RES.CORN, RES.SPICES, RES.COCOA, RES.GRAPES, RES.HONEYCOMBS, RES.HOPS)

	# TODO: add collectors for handling primary resources transport from fields
	for a, b in zip(primary_resources, secondary_resources):
		assert farm.get_component(StorageComponent).inventory[a] == 0
		farm.get_component(StorageComponent).inventory.alter(a, 2) # 2 potatoes give 1 unit of food
		
		s.run(seconds=5)
		assert farm.get_component(StorageComponent).inventory[b]


@game_test()
def test_school_production(s, p):
	"""
	Check whether schools produce education
	"""
	settlement, island = settle(s)
	school = Build(BUILDINGS.VILLAGE_SCHOOL, 30, 30, island, settlement=settlement)(p)
	
	assert school
	
	assert school.get_component(StorageComponent).inventory[RES.EDUCATION] == 0
	s.run(seconds=30)
	assert school.get_component(StorageComponent).inventory[RES.EDUCATION]


@game_test()
def test_saltpond_production(s, p):
	"""
	Check whether saltponds produce salt
	"""
	settlement, island = settle(s)
	saltpond = Build(BUILDINGS.SALT_PONDS, 25, 20, island, settlement=settlement)(p)
	
	assert saltpond
	
	assert saltpond.get_component(StorageComponent).inventory[RES.SALT] == 0
	s.run(seconds=60)
	assert saltpond.get_component(StorageComponent).inventory[RES.SALT] >= 2 # ponds produce salt in units of 2
	

@game_test()
def test_distillery_production_chain(s, p):
	"""
	Raw sugar is generated by sugarcane fields and transferred to the distillery 
	for liquor production
	"""
	settlement, island = settle(s)
	
	assert Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.SUGARCANE_FIELD, 26, 30, island, settlement=settlement)(p)
	
	distillery = Build(BUILDINGS.DISTILLERY, 30, 26, island, settlement=settlement)(p)
	
	assert distillery
	
	assert distillery.get_component(StorageComponent).inventory[RES.SUGAR] == 0
	assert distillery.get_component(StorageComponent).inventory[RES.LIQUOR] == 0
	s.run(seconds=60) # 30s sugarcane field, 12s distillery
	assert distillery.get_component(StorageComponent).inventory[RES.LIQUOR]
	

@game_test()
def test_brewery_production_chain(s, p):
	"""
	Hops are generated by hop fields and transferred to the brewery for beer production
	"""
	settlement, island = settle(s)
	
	assert Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.HOP_FIELD, 26, 30, island, settlement=settlement)(p)
	
	brewery = Build(BUILDINGS.BREWERY, 30, 26, island, settlement=settlement)(p)
	
	assert brewery
	
	assert brewery.get_component(StorageComponent).inventory[RES.HOPS] == 0
	assert brewery.get_component(StorageComponent).inventory[RES.BEER] == 0
	s.run(seconds=60) # 26s hop field, 12s brewery
	assert brewery.get_component(StorageComponent).inventory[RES.BEER]


@game_test()
def test_tobbaconist_production_chain(s, p):
	"""
	Tobacco is generated by tobacco fields and transferred to the tobacconist for tobacco
	products making
	"""
	settlement, island = settle(s)
	
	assert Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.TOBACCO_FIELD, 26, 30, island, settlement=settlement)(p)
	
	tobacconist = Build(BUILDINGS.TOBACCONIST, 30, 26, island, settlement=settlement)(p)
	
	assert tobacconist
	
	assert tobacconist.get_component(StorageComponent).inventory[RES.TOBACCO_LEAVES] == 0
	assert tobacconist.get_component(StorageComponent).inventory[RES.TOBACCO_PRODUCTS] == 0
	s.run(seconds=120) # 30s tobacco field, 15s tobacconist
	assert tobacconist.get_component(StorageComponent).inventory[RES.TOBACCO_PRODUCTS]
	

@game_test()
def test_butchery_production_chain(s, p):
	"""
	Pigs and cattle are herded at a farm and processed into meat at the butchery
	"""
	settlement, island = settle(s)
	
	assert Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.CATTLE_RUN, 26, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.PIGSTY, 30, 34, island, settlement=settlement)(p)
	
	butchery = Build(BUILDINGS.BUTCHERY, 30, 26, island, settlement=settlement)(p)
	
	assert butchery
	
	assert butchery.get_component(StorageComponent).inventory[RES.PIGS_SLAUGHTER] == 0
	assert butchery.get_component(StorageComponent).inventory[RES.CATTLE_SLAUGHTER] == 0
	assert butchery.get_component(StorageComponent).inventory[RES.FOOD] == 0
	s.run(seconds=200) # 40s cattlerun, 60s pigsty, 2x 15s butchery
	assert butchery.get_component(StorageComponent).inventory[RES.FOOD] >= 4 # each meat gives 2 units of food
	

@game_test()
def test_bakery_production_chain(s, p):
	"""
	Corn is grown in cornfields, milled into flour in a windmill and finally turned into food by a bakery
	"""
	settlement, island = settle(s)
	
	assert Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.CORN_FIELD, 26, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.WINDMILL, 30, 34, island, settlement=settlement)(p)
	
	bakery = Build(BUILDINGS.BAKERY, 30, 26, island, settlement=settlement)(p)
	
	assert bakery
	
	assert bakery.get_component(StorageComponent).inventory[RES.FLOUR] == 0
	assert bakery.get_component(StorageComponent).inventory[RES.FOOD] == 0
	s.run(seconds=120) # 26s cornfield, 15s windmill, 15s bakery
	assert bakery.get_component(StorageComponent).inventory[RES.FOOD]
	
@game_test()
def test_blender_production_chain(s, p):
	"""
	Spices are grown in spice fields and processed by the blender into condiments
	"""
	settlement, island = settle(s)
	
	assert Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.SPICE_FIELD, 26, 30, island, settlement=settlement)(p)
	
	blender = Build(BUILDINGS.BLENDER, 30, 26, island, settlement=settlement)(p)
	
	assert blender
	
	assert blender.get_component(StorageComponent).inventory[RES.CONDIMENTS] == 0
	assert blender.get_component(StorageComponent).inventory[RES.SPICES] == 0
	s.run(seconds=120) # 2x 30s spicefield, 15s blender
	assert blender.get_component(StorageComponent).inventory[RES.CONDIMENTS]


@game_test()
def test_doctor_curing_chain(s, p):
	"""
	Medical herbs are grown in herbaries and later used for curing the Black Death by the doctor
	"""
	settlement, island = settle(s)
	
	assert Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.HERBARY, 26, 30, island, settlement=settlement)(p)
	
	doctor = Build(BUILDINGS.DOCTOR, 30, 26, island, settlement=settlement)(p)
	
	assert doctor
	
	assert doctor.get_component(StorageComponent).inventory[RES.MEDICAL_HERBS] == 0
	assert doctor.get_component(StorageComponent).inventory[RES.BLACKDEATH] == 0
	
	# simulate a Black Death occurence
	doctor.get_component(StorageComponent).inventory.alter(RES.BLACKDEATH, 1)
	s.run(seconds=120) # 2x 30s herbary, 60s doctor
	assert doctor.get_component(StorageComponent).inventory[RES.MEDICAL_HERBS]
	assert doctor.get_component(StorageComponent).inventory[RES.BLACKDEATH] == 0 # Black Death eliminated
	

@game_test()
def test_winery_production_chain(s, p):
	"""
	Grapes are grown in a vineyard processed into liquor at a winery
	"""
	settlement, island = settle(s)
	
	assert Build(BUILDINGS.FARM, 30, 30, island, settlement=settlement)(p)
	assert Build(BUILDINGS.VINEYARD, 26, 30, island, settlement=settlement)(p)
	
	winery = Build(BUILDINGS.WINERY, 30, 26, island, settlement=settlement)(p)
	
	assert winery
	
	assert winery.get_component(StorageComponent).inventory[RES.GRAPES] == 0
	assert winery.get_component(StorageComponent).inventory[RES.LIQUOR] == 0
	s.run(seconds=120) # 2x 30s vineyard, 15s winery
	assert winery.get_component(StorageComponent).inventory[RES.LIQUOR]
